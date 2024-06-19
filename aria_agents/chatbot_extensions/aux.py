from pydantic import BaseModel, Field

class PapersSummary(BaseModel):
    """A summary of the papers found in the PubMed Central database search"""
    state_of_field : str = Field(description="A summary of the current state of the field")
    open_questions : str = Field(description="A summary of the open questions in the field")