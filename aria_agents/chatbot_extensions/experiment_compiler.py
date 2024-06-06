import dotenv
dotenv.load_dotenv()
import os
from typing import List, Optional, Union, Type, Any, get_type_hints, Tuple, Literal, Dict, Any
from typing_extensions import Self
import asyncio
import pickle as pkl
from schema_agents import schema_tool, Role
import json
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Union
import argparse
from typing import Union, List, Dict
import copy
from aria_agents.chatbot_extensions.aux_classes import SuggestedStudy
from tqdm.auto import tqdm

def extract_uids(instance: BaseModel, uid_set: Dict[str, BaseModel] = {}) -> Dict[str, BaseModel]:
        """ Recursively extracts unique uids from Pydantic model instances. """
        if hasattr(instance, 'uid'):
            uid_set[instance.uid] = instance

        # Iterate over all attributes of the instance
        for attr_value in instance.__dict__.values():
            if isinstance(attr_value, BaseModel):
                # Recurse into another BaseModel instance
                uid_set.update(extract_uids(attr_value, uid_set))
            elif isinstance(attr_value, list):
                # Recurse into each item if it is a list containing BaseModel instances
                for item in attr_value:
                    if isinstance(item, BaseModel):
                        uid_set.update(extract_uids(item, uid_set))
        return uid_set

def initialize_models(investigation : BaseModel, assay_prefix = "a", study_prefix = "s"):
    uid_ignore_fields = ['uid', 'data_files', 'process_sequences', 'executes_protocols', 'technology_types', 'sources', 'samples', 'data_files', 'assays', 'protocol_types', "measurement_types"]
    uid_basemodels = extract_uids(copy.deepcopy(investigation))
    uid_isa = {}
    model_types  = list(set([x._model.__name__ for x in uid_basemodels.values()]))
    model_order = ['Comment', 'OntologySource', 'OntologyAnnotation', 'Characteristic', 'ProtocolParameter', 'Protocol', 'Material', 'Source', 'StudyFactor', 'FactorValue', 'Sample', 'ParameterValue', 'DataFile', 'Process', 'Assay', 'Study', 'Investigation']
    order_index = {key : index for index, key in enumerate(model_order)}
    for model_type in sorted(model_types, key = lambda x : order_index[x]):
        pyd_instances = [x for x in uid_basemodels.values() if x._model.__name__ == model_type]
        for pyd_instance in pyd_instances:
            model_args = {field_name : field_value for field_name, field_value in pyd_instance if field_name not in uid_ignore_fields and not (field_name.endswith('_uids') or field_name.endswith('_uid'))}
            if 'title_' in model_args:
                model_args_new = {k : v for k,v in model_args.items() if k != 'title_'}
                model_args_new['title'] = model_args['title_']
                model_args = model_args_new
            # if model_type == 'Assay':
                # sys.exit()
            for k,v in model_args.items():
                if isinstance(v, BaseModel):
                    model_args[k] = uid_isa[v.uid]
                elif isinstance(v, list):
                    for i_x, x in enumerate(v):
                        if isinstance(x, BaseModel):
                            v[i_x] = uid_isa[x.uid]
            # model_args['identifier'] = pyd_instance.uid
            m = pyd_instance._model(**model_args)
            uid_pointer_fields = [field_name for field_name, field_value in pyd_instance if field_name.endswith('_uids') or field_name.endswith('_uid')]
            for upf in uid_pointer_fields:
                if type(getattr(pyd_instance, upf)) == list:
                    setattr(m, upf.replace('_uids', ''), [uid_isa[x] for x in getattr(pyd_instance, upf)]) 
                else:
                    setattr(m, upf.replace('_uid', ''), uid_isa[getattr(pyd_instance, upf)])
            uid_isa[pyd_instance.uid] = m
        # if model_type == 'Assay':
        #     return m, pyd_instance, model_args, uid_isa, uid_basemodels
        if model_type == 'Investigation':
            m_i = m
    for i_study, study in enumerate(m_i.studies):
        study.filename = f"{study_prefix}_{i_study}.tsv"
        for i_assay, assay in enumerate(study.assays):
            assay.filename = f"{assay_prefix}_{i_assay}.tsv"
    return m_i, uid_isa


class ExperimentalProtocol(BaseModel):
    """A detailed list of steps outlining an experimental procedure that to be carried out in the lab. The steps MUST be detailed enough for a new student to follow them exactly without any questions or doubts.
Do not include any data analysis portion of the study, only the procedure through the point of data collection. That means no statistical tests or data processing should be included unless they are necessary for downstream data collection steps."""
    steps : str = Field(..., description="A list of steps that must be followed in order to carry out the experiment. This string MUST be in markdown format and should contain no irregular characters.")

class ProtocolFeedback(BaseModel):
    """The expert scientist's feedback on a protocol"""
    complete : bool = Field(..., description="Whether the protocol is specified in enough detail for a new student to follow it exactly without any questions or doubts")
    feedback : str = Field(..., description="The expert scientist's feedback on the protocol")


async def get_protocol_feedback(protocol : ExperimentalProtocol, protocol_manager : Role) -> ProtocolFeedback:
    res = await protocol_manager.aask(["Is the following protocol specified in enough detail for a new student to follow it exactly without any questions or doubts? If not, say why.", protocol], output_schema=ProtocolFeedback)
    return res

async def revise_protocol(protocol : ExperimentalProtocol, feedback : ProtocolFeedback, protocol_writer : Role) -> ExperimentalProtocol:
    res = await protocol_writer.aask(["Take the following feedback and use it to revise the protocol to be more detailed. First the protocol will be provided, then the feedback.", protocol, feedback], output_schema=ExperimentalProtocol)
    return res


project_folders = os.environ.get('PROJECT_FOLDERS', './projects')
os.makedirs(project_folders, exist_ok = True)

LLM_MODEL = 'gpt-4o'

@schema_tool
async def run_experiment_compiler(
    project_name: str = Field(description = "The name of the project, used to create a folder to store the output files and to read input files from the study suggester run"),
    constraints: str = Field("", description = "Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc."),
    max_revisions: int = Field(10, description = "The maximum number of protocol revision rounds to allow")
):
    """Generate an investigation from a suggested study"""
    project_folder = os.path.join(project_folders, project_name)
    os.makedirs(project_folder, exist_ok = True)
    
    
    protocol_writer = Role(name="Protocol Writer",
                    instructions="""You are an extremely detail oriented student who works in a biological laboratory. You read protocols and revise them to be specific enough until you and your fellow students could execute the protocol yourself in the lab.
    You do not conduct any data analysis, only data collection so your protocols only include steps up through the point of collecting data, not drawing conclusions.""",
                    constraints=constraints,
                    register_default_events=True,
                    model=LLM_MODEL)

    protocol_manager = Role(name="Protocol manager",
                        instructions="You are an expert laboratory scientist. You read protocols and manage them to ensure that they are clear and detailed enough for a new student to follow them exactly without any questions or doubts.",
                        constraints=constraints,
                        register_default_events=True,
                        model=LLM_MODEL)

    # request = f"""Take the suggested study and turn in into a fully-specific investigation (while considering the constraints). You are being asked to create an investigation draft which contains ALL the components you'll need to test the hypothesis.
    # Note that each assay will ultimately be assigned a single `measurement_type` (from `measurement_types`) and `technology_type` (from `technology_types`) pair. You MUST ensure that every assay's (measurement_type, technology_type) term pair is one of these (picking the most appropriate AND being case-sensitive): [(metabolite profiling,NMR spectroscopy),(targeted metabolite profiling,NMR spectroscopy),(untargeted metabolite profiling,NMR spectroscopy),(isotopomer distribution analysis,NMR spectroscopy),(metabolite profiling,mass spectrometry),(targeted metabolite profiling,mass spectrometry),(untargeted metabolite profiling,mass spectrometry),(isotologue distribution analysis,mass spectrometry),(transcription profiling,DNA microarray),(genotype profiling,DNA microarray),(epigenome profiling,DNA microarray),(exome profiling,DNA microarray),(DNA methylation profiling,DNA microarray),(copy number variation profiling,DNA microarray),(transcription factor binding site identification,DNA microarray),(protein-DNA binding site identification,DNA microarray),(SNP analysis,DNA microarray),(transcription profiling,nucleic acid sequencing),(transcription factor binding site identification,nucleic acid sequencing),(protein-DNA binding site identification,nucleic acid sequencing),(DNA methylation profiling,nucleic acid sequencing),(histone modification profiling,nucleic acid sequencing),(genome sequencing,nucleic acid sequencing),(metagenome sequencing,nucleic acid sequencing),(environmental gene survey,nucleic acid sequencing),(cell sorting,flow cytometry),(cell counting,flow cytometry),(cell migration assay,microscopy imaging),(phenotyping,imaging),(transcription profiling,RT-pcr)]
    # """
    suggested_study_json = os.path.join(project_folder, "suggested_study.json")
    suggested_study = SuggestedStudy(**json.loads(open(suggested_study_json).read()))
    protocol = await protocol_writer.aask(["Take the following suggested study and use it to produce a detailed protocol telling a student exactly what steps they should follow in the lab to collect data. Do not include any data analysis or conclusion-drawing steps, only data collection.", suggested_study], output_schema=ExperimentalProtocol)
    protocol_feedback = await get_protocol_feedback(protocol, protocol_manager)
    revisions = 0
    pbar = tqdm(total=max_revisions)
    while not protocol_feedback.complete and revisions < max_revisions:
        protocol = await revise_protocol(protocol, protocol_feedback, protocol_writer)
        protocol_feedback = await get_protocol_feedback(protocol, protocol_manager)
        revisions += 1
    pbar.update(1)
    pbar.close()
    protocol_json = os.path.join(project_folder, "protocol.json")
    with open(protocol_json, 'w') as f:
        f.write(protocol.json())
    return {
        "protocol": protocol.dict(),
    }

async def main():
    parser = argparse.ArgumentParser(description='Generate an investigation')
    parser.add_argument('--project_name', type = str, help = 'The name of the project', required = True)
    parser.add_argument('--max_revisions', type = int, help = 'The maximum number of protocol agent revisions to allow', default = 10)
    # parser.add_argument('--suggested_study_json', type = str, required = True, help = 'A json file containing a serialized study suggestion')
    # parser.add_argument('--hypothesis', type = str, help = 'The hypothesis to test', required = True)
    # parser.add_argument('--project_folder', type=str, help='The directory to save the investigation to', default = 'investigation')
    args = parser.parse_args()
    await run_experiment_compiler(**vars(args))




if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)