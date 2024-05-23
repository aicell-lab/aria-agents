from pydantic import BaseModel, Field
from typing import List

class SuggestedStudy(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge"""
    user_request : str = Field(description = "The original user request")
    experiment_name : str = Field(description = "The name of the experiment")
    experiment_material : List[str] = Field(description = "The materials required for the experiment")
    experiment_expected_results : str = Field(description = "The expected results of the experiment")
    experiment_protocol : List[str] = Field(description = "The protocol steps for the experiment")
    experiment_hypothesis : str = Field(description = "The hypothesis to be tested by the experiment")