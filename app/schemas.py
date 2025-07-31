from pydantic import BaseModel, Field, EmailStr


class CreateUser(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr = Field(
        ...,
        examples=["user@example.com"],
        description="Valid email address"
    )
    password: str
