import enum
from datetime import datetime, date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Float,
    Table,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Таблицы связей (Association Tables)
movie_actors = Table(
    "movie_actors",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id"), primary_key=True),
    Column("actor_id", ForeignKey("actors.id"), primary_key=True),
)

movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id"), primary_key=True),
)


class UserGroupEnum(enum.Enum):
    USER = "user"
    ADMIN = "admin"


class UserGroupModel(Base):
    __tablename__ = "user_groups"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # e.g., "user", "admin"


class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    group_id = Column(Integer, ForeignKey("user_groups.id"))

    group = relationship("UserGroupModel")
    profile = relationship("UserProfileModel", back_populates="user", uselist=False)
    activation_token = relationship(
        "ActivationTokenModel", back_populates="user", uselist=False
    )


class UserProfileModel(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    first_name = Column(
        String(50), nullable=False
    )  # Тесты ожидают нижний регистр при сохранении
    last_name = Column(String(50), nullable=False)
    gender = Column(String(20))
    date_of_birth = Column(Date)
    info = Column(String(500))
    avatar = Column(String)  # Путь/ключ к файлу в S3

    user = relationship("UserModel", back_populates="profile")


class ActivationTokenModel(Base):
    __tablename__ = "activation_tokens"
    id = Column(Integer, primary_key=True)
    token = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("UserModel", back_populates="activation_token")


class MovieModel(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    score = Column(Float)
    # Другие поля (год, описание) согласно seed_database

    genres = relationship("GenreModel", secondary=movie_genres)
    actors = relationship("ActorModel", secondary=movie_actors)


class GenreModel(Base):
    __tablename__ = "genres"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)


class ActorModel(Base):
    __tablename__ = "actors"
    id = Column(Integer, primary_key=True)
    name = Column(String)
