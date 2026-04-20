# POST /auth/register  →  creates a new user (max 2 only)
# POST /auth/login     →  checks credentials, returns JWT token
# GET  /auth/me        →  returns logged-in user info (requires token)

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
import os
import time

from database import get_db
from models.db_models import User

router = APIRouter()

# ─────────────────────────────────────────
# Config
# ─────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

MAX_USERS = 2  # core limit of your project
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_LOCKOUT_SECONDS = 15 * 60
login_attempts = {}


# ─────────────────────────────────────────
# Pydantic Schemas (request/response shapes)
# ─────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    name: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime


# ─────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────

def hash_password(password: str) -> str:
    """Convert plain password to hashed version for DB storage"""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Check if entered password matches stored hash"""
    return pwd_context.verify(plain, hashed)

def create_access_token(user_id: str) -> str:
    """Generate JWT token containing user_id"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,   # 'sub' = subject (standard JWT field)
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _login_attempt_key(identifier: str, ip_address: str) -> str:
    return f"{identifier.lower()}|{ip_address}"


def _prune_attempt_record(record: dict, now: float):
    record["attempts"] = [timestamp for timestamp in record["attempts"] if now - timestamp <= LOGIN_WINDOW_SECONDS]


def check_login_throttle(identifier: str, ip_address: str):
    key = _login_attempt_key(identifier, ip_address)
    now = time.time()
    record = login_attempts.get(key, {"attempts": [], "locked_until": 0.0})
    _prune_attempt_record(record, now)

    if record["locked_until"] > now:
      retry_after = max(1, int(record["locked_until"] - now))
      raise HTTPException(
          status_code=429,
          detail=f"Too many login attempts. Try again in {retry_after} seconds."
      )

    login_attempts[key] = record


def record_failed_login(identifier: str, ip_address: str):
    key = _login_attempt_key(identifier, ip_address)
    now = time.time()
    record = login_attempts.get(key, {"attempts": [], "locked_until": 0.0})
    _prune_attempt_record(record, now)
    record["attempts"].append(now)

    if len(record["attempts"]) >= LOGIN_MAX_ATTEMPTS:
        record["locked_until"] = now + LOGIN_LOCKOUT_SECONDS

    login_attempts[key] = record


def clear_login_throttle(identifier: str, ip_address: str):
    key = _login_attempt_key(identifier, ip_address)
    login_attempts.pop(key, None)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    This function runs on every protected route.
    It reads the token from the Authorization header,
    decodes it, finds the user and returns them.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user  # ← the actual User object from DB


# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@router.post("/register", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    
    # 1. Check 2 user limit
    user_count = db.query(User).count()
    if user_count >= MAX_USERS:
        raise HTTPException(
            status_code=400,
            detail="Maximum 2 users allowed. Registration is closed."
        )

    # 2. Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 3. Create new user
    new_user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password)  # NEVER store plain password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully", "user_id": str(new_user.id)}


@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # OAuth2PasswordRequestForm expects 'username' field
    # we use email as the username

    ip_address = request.client.host if request.client else "unknown"
    check_login_throttle(form_data.username, ip_address)

    # 1. Find user by email
    user = db.query(User).filter(User.email == form_data.username).first()

    # 2. Verify password
    if not user or not verify_password(form_data.password, user.password_hash):
        record_failed_login(form_data.username, ip_address)
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    # 3. Update last_active
    clear_login_throttle(form_data.username, ip_address)
    user.last_active = datetime.utcnow()
    db.commit()

    # 4. Generate and return JWT token
    token = create_access_token(str(user.id))

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "name": user.name
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Protected route — requires valid JWT token.
    Returns the logged-in user's info.
    """
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "created_at": current_user.created_at
    }
