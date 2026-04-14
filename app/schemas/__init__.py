from app.schemas.schemas import (  # noqa: F401
    UserOut,
    UserUpdate,
    CourseCreate,
    CourseUpdate,
    CourseOut,
    LessonCreate,
    LessonUpdate,
    LessonOut,
    LessonSummaryOut,
    QuestionOut,
    QuizOut,
    QuizQuestionIn,
    QuizSubmit,
    QuizUpdate,
    QuizResultOut,
    PromptBlockIn,
    PromptCreate,
    PromptOut,
    AdminUserOut,
)

from app.schemas.auth import (
    GoogleLoginRequest,
    TokenResponse,
    RefreshRequest,
)