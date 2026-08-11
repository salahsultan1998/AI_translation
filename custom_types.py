from pydantic import BaseModel, Field
from typing import List, Optional

class RowItem(BaseModel):
    """A single row item inside a translation batch."""
    row_id: int
    source_text: str = Field(description="Original Chinese string.")
    context: Optional[str] = Field(default=None, description="Speaker, UI category, or context note if available.")

class BatchTranslationRequest(BaseModel):
    """Payload sent to the Translator Agent containing a user-defined window of lines."""
    batch_id: int
    rows: List[RowItem]
    target_language: str = "Arabic"

class SingleRowResult(BaseModel):
    """Translated output for an individual row within a batch."""
    row_id: int
    translated_text: str = Field(description="Localized text in the target language for this specific row.")

class BatchTranslationResponse(BaseModel):
    """Structured response from the LLM for the entire batch."""
    batch_id: Optional[int] = None
    translations: List[SingleRowResult]

class ReviewResult(BaseModel):
    """Validation result from the Reviewer Agent for the entire batch."""
    is_valid: bool = Field(description="True if all variables, placeholders, tags, and formatting were preserved verbatim.")
    feedback_prompt: str = Field(default="", description="Correction feedback explaining errors if validation fails.")