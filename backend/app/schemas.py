from pydantic import BaseModel, Field, field_validator, model_validator


class QuestionCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)
    choices: list[str] = Field(min_length=2, max_length=4)
    correct_choice_index: int = Field(ge=0, le=3)
    time_limit_seconds: int = Field(ge=5, le=300)

    @field_validator("prompt")
    @classmethod
    def trim_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question prompt cannot be blank")
        return value

    @field_validator("choices")
    @classmethod
    def clean_choices(cls, values: list[str]) -> list[str]:
        values = [value.strip() for value in values]
        if any(not value or len(value) > 200 for value in values):
            raise ValueError("Each answer must contain 1–200 characters")
        return values

    @model_validator(mode="after")
    def correct_choice_exists(self):
        if self.correct_choice_index >= len(self.choices):
            raise ValueError("Correct answer must point to one of the choices")
        return self


class QuizCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    questions: list[QuestionCreate] = Field(min_length=1, max_length=20)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Quiz title cannot be blank")
        return value


class ParticipantJoin(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    display_name: str = Field(min_length=1, max_length=32)

    @field_validator("name", "display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value
