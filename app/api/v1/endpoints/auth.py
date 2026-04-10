from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Annotated, Any

from app.db.session import get_db
from app.crud import get_user_by_username, create_user
from app.schemas import Token, UserCreate, UserResponse
from app.core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.hashing import Hasher

import logging

logger = logging.getLogger(__name__)
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

@router.post("/login", response_model=Token)
def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Any = Depends(get_db)):
    logger.debug(f"Login attempt for user: {form_data.username}")
    
    # Explicitly check for empty credentials (though OAuth2PasswordRequestForm should handle it)
    if not form_data.username or not form_data.password:
        logger.warning(f"Empty credentials provided for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )
        
    try:
        user = get_user_by_username(db, form_data.username)
        
        password_hash = getattr(user, "password_hash", None)
        if not user or not password_hash or not Hasher.verify_password(form_data.password, password_hash):
            logger.warning(f"Failed login attempt for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"Successful login for user: {form_data.username}")
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.username, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login for user {form_data.username}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Any = Depends(get_db)):
    db_user = get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    try:
        return create_user(db=db, user=user)
    except Exception as e:
        logger.error(f"Error during registration for user {user.username}: {str(e)}", exc_info=True)
        
        error_msg = str(e).lower()
        if "unique" in error_msg or "constraint" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Username already registered"
            )
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )
