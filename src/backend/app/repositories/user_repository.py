from datetime import datetime
from typing import List, Optional, Union
from sqlalchemy import UUID
from sqlalchemy.orm import joinedload
from sqlmodel import Session, select
from domain.dto.profile import UserProfileDto
from domain.mapping import map_hobby_data, map_skill_data, delete_hobby_data, map_discipline_data
from domain.schema.user import User, UserIdentifiers, UserProfile
from common.database import engine
from app.utilities.database import recursive_load_options

class UserRepository:
    """
    Handles all primary data access for user records in the database
    """
    async def create_user(self, email_address: str, username: str, password_hash: str) -> User:
        """
        Creates a new ueer record in the database

        Args:
            email_address (str): The user's email address
            username (str): The unique name for the user
            password_hash (str): A hash derived from the user's password

        Returns:
            User: The newly created user record
        """
        user = User(email=email_address, username=username, password_hash=password_hash)
        user.profile = UserProfile()
        
        with Session(engine) as session:
            session.add(user)
            session.commit()
            session.refresh(user)
        
        return user
    
    async def upsert_profile(self, user_id: UUID, profile: UserProfileDto):
        """
        Creates or replaces a user profile record in the database

        Args:
            user_id (UUID): The ID of the user to associate the profile with
            profile (UserProfile): The profile data to store
        """
        with Session(engine) as session:
            user_query = select(User).where(User.id == user_id).options(joinedload(User.profile))
            resultset = session.exec(user_query)
            
            user = resultset.first()
            if user is None:
                return None
            
            user.profile.first_name = profile.first_name
            user.profile.last_name = profile.last_name
            user.profile.bio = profile.bio
            user.profile.github_username = profile.github_username
            user.profile.birthdate = profile.birthdate

            map_discipline_data(session, user.profile, profile.disciplines)
            map_skill_data(session, user.profile, profile.skills)
            
            if profile.hobby:
                map_hobby_data(session, user.profile.id, profile.hobby)
            elif user.profile.hobby:
                delete_hobby_data(session, user.profile.hobby)
                
            if profile.student:
                user.profile.student = profile.student
            elif user.profile.student:
                session.delete(user.profile.student)
                
            if profile.professional:
                user.profile.professional = profile.professional
            elif user.profile.professional:
                session.delete(user.profile.professional)
                
            session.commit()
            
    async def set_avatar_url(self, user_id: UUID, avatar_url: str) -> None:
        """
        Sets the avatar URL for a user

        Args:
            user_id (UUID): The ID of the user to set the avatar for
            avatar_url (str): The URL of the avatar
        """
        with Session(engine) as session:
            query = select(User).where(User.id == user_id).options(joinedload(User.profile))
            resultset = session.exec(query)
            
            user = resultset.first()
            
            if not user:
                return
            
            if not user.profile:
                return
            
            user.profile.avatar_url = avatar_url
            
            session.commit()
    
    async def get_user(self, by: UserIdentifiers, value: Union[str, UUID], include: Optional[List[str]] = []) -> Optional[User]:
        """
        Retrieves a user by one of their unique identifiers, optionally joining related data

        Args:
            by (UserIdentifiers): The type of identifier to search by
            value (Union[str, UUID]): The value of the identifier
            include (Optional[List[UserIncludes]], optional): A list of relationships to populate. Defaults to [].

        Returns:
            Optional[User]: The user record if found, otherwise None
        """
        with Session(engine) as session:
            query = select(User)
            if by == "id":
                query = query.where(User.id == value)
            elif by == "username":
                query = query.where(User.username == value)
            elif by == "email":
                query = query.where(User.email == value)
            elif by == "verification_code":
                query = query.where(
                    User.verification_code == value and 
                    User.pending_verification == True and 
                    User.verification_code is not None
                )
            
            if include:
                for field in include:
                    query = query.options(*recursive_load_options(User, field))
        
            resultset = session.exec(query)
            
            return resultset.first()
        
    async def set_verification_code(self, user_id: UUID, code: str) -> None:
        """
        Sets the verification code for a user

        Args:
            user_id (UUID): The ID of the user to set the code for
            code (str): The verification code to set
        """
        with Session(engine) as session:
            query = select(User).where(User.id == user_id)
            resultset = session.exec(query)
            
            user = resultset.first()
            user.pending_verification = True
            user.verification_sent_at_utc = datetime.utcnow()
            user.verification_code = code
            
            session.commit()
            
    async def mark_verified(self, user_id: UUID) -> None:
        """
        Marks a user as verified

        Args:
            user_id (UUID): The ID of the user to mark
        """
        with Session(engine) as session:
            query = select(User).where(User.id == user_id)
            resultset = session.exec(query)
            
            user = resultset.first()
            user.pending_verification = False
            user.verification_code = None
            
            session.commit()