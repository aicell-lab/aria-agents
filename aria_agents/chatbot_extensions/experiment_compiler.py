import dotenv
dotenv.load_dotenv()
import os
from typing import List, Optional, Union, Type, Any, get_type_hints, Tuple, Literal, Dict, Any
from typing_extensions import Self
import asyncio
import pickle as pkl
from schema_agents import Role
import json
from pydantic import BaseModel, Field, model_validator
from isatools import model
from typing import List, Optional, Union
from isatools import isajson
import argparse
from typing import Union, List, Dict
import copy
from aux_classes import SuggestedStudy

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

class PydComment(BaseModel):
    """Represents a free-text comment on aspects of the scientific investigation. Comments are helpful to explain decision choices and details that will help the experimenter carry out the investigation."""
    name : str = Field(..., description="A very short name for the comment for future reference")
    value : str = Field(..., description="The content of the comment. ")
    uid : str = Field(..., description="An identifier for the comment that is unique across all objects types across the entire investigation. E.g. PydComment-0001")
    _model = model.Comment

class PydOntologySource(BaseModel):
    name : str = Field(..., description = "The name of the source of a term; i.e. the source controlled vocabulary or ontology.")
    file : str = Field(..., description = "A file name or a URI of an official resource.")
    version : str = Field(..., description = "The version number of the Term Source to support terms tracking.")
    description : str = Field(..., description = "A free text description of the resource.")
    comments : Optional[List[PydComment]] = Field(None, description = "Comments associated with instances of this class.")
    uid : str = Field(..., description = "An identifier for the ontology source that is unique across all objects types across the entire investigation. E.g. PydOntologySource-0001")
    _model =  model.OntologySource

class PydOntologyAnnotation(BaseModel):
    """An ontology annotation"""
    term : str = Field(..., description = "A term taken from an ontology or controlled vocabulary.")
    # term_source : PydOntologySource = Field(..., description = "Reference to the OntologySource from which the term is derived.")
    # term_accession : Optional[str] = Field('', description = "A URI or resource-specific identifier for the term.")
    comments : Optional[List[PydComment]] = Field(None, description = "Comments associated with instances of this class.")
    uid : str = Field(..., description = "An identifier for the ontology annotation that is unique across all objects types across the entire investigation. E.g. PydOntologyAnnotation-0001")
    _model = model.OntologyAnnotation

class PydCharacteristic(BaseModel):
    """A Characteristic acts as a qualifying property to a material object."""
    category : Optional[PydOntologyAnnotation] = Field(None, description = "The classifier of the type of characteristic being described. If provided, MUST be a `PydOntologyAnnotation` object.")
    value : Optional[Union[str, int, float, PydOntologyAnnotation]] = Field(None, description = "The value of this instance of a characteristic as relevant to the attached material.")
    unit : Optional[Union[PydOntologyAnnotation, str]] = Field(None, description = "If applicable, a unit qualifier for the value (if the value is numeric).")
    comments : Optional[List[PydComment]] = Field(None, description = "Comments associated with instances of this class.")
    uid : str = Field(..., description = "An identifier for the characteristic that is unique across all objects types across the entire investigation. E.g. PydCharacteristic-0001")
    _model = model.Characteristic

    @model_validator(mode = 'after')
    # @classmethod
    def check_self(self) -> Self:
        """Check that `category` is a `PydOntologyAnnotation` object"""
        if self.category is not None:
            if not isinstance(self.category, PydOntologyAnnotation):
                raise ValueError(f"Category must be a `PydOntologyAnnotation` object. Right now it is a `{type(self.category)}` with value `{self.category}`")
        return self

class PydProtocolParameter(BaseModel):
    """A parameter used by a protocol."""
    parameter_name : Optional[PydOntologyAnnotation] = Field(None, description = "A parameter name as an ontology term.")
    comments : Optional[List[PydComment]] = Field(None, description = "Comments associated with instances of this class.")
    uid : str = Field(..., description = "An identifier for the protocol parameter that is unique across all objects types across the entire investigation. E.g. PydProtocolParameter-0001")
    _model = model.ProtocolParameter

class PydProtocol(BaseModel):
    """An experimental Protocol used in the study."""
    name : str = Field(..., description = "The name of the protocol used.")
    protocol_type_uid : str = Field(..., description = "An ontology source reference of the protocol type. The string is the UID of the PydOntologyAnnotation object.")
    description : str = Field(..., description = "A free-text description of the protocol.")
    uid : str = Field(..., description = "An identifier for the protocol that is unique across all objects types across the entire investigation. E.g. PydProtocol-0001")
    _model = model.Protocol

class PydMaterial(BaseModel):
    """Represents a generic material in an experimental graph."""
    name : str = Field(..., description = "The name of the material")
    type_ : str = Field(..., description="The type of the material") 
    comments : Optional[List[PydComment]] = Field(None, description = "Comments associated with instances of this class.")
    uid : str = Field(..., description = "An identifier for the material that is unique across all objects types across the entire investigation. E.g. PydMaterial-0001")
    _model =  model.Material
 
class PydSource(BaseModel):
    """Represents a Source material in an experimental graph."""
    name : str = Field(..., description = "A name/reference for the source material.")
    comments : Optional[List[PydComment]] = Field(None, description = "Comments associated with instances of this class.")
    uid : str = Field(..., description = "An identifier for the source that is unique across all objects types across the entire investigation. E.g. PydSource-0001")
    _model =  model.Source

class PydStudyFactor(BaseModel):
    """A Study Factor corresponds to an independent variable manipulated by the experimentalist with the intention to affect biological systems in a way that can be measured by an assay."""
    name : str = Field(..., description = "Study factor name")
    factor_type : Optional[PydOntologyAnnotation] = Field(None, description = "An ontology source reference of the study factor type")
    comments : Optional[List[PydComment]] = Field(None, description = "Comments associated with instances of this class.")
    uid : str = Field(..., description = "An identifier for the study factor that is unique across all objects types across the entire investigation. E.g. PydStudyFactor-0001")
    _model = model.StudyFactor

class PydFactorValue(BaseModel):
    """A FactorValue represents the value instance of a StudyFactor."""
    factor_name : Optional[PydStudyFactor] = Field(None, description = "Reference to an instance of a relevant StudyFactor.")
    value : Optional[Union[str, int, float, PydOntologyAnnotation]] = Field(None, description = "The value of the factor at hand.")
    unit : Optional[PydOntologyAnnotation] = Field(None, description = "If numeric, the unit qualifier for the value.")
    comments : List[PydComment] = Field(..., description = "Helpful comments to inform the experimenter about the specifics of the factor value.")
    uid : str = Field(..., description = "An identifier for the factor value that is unique across all objects types across the entire investigation. E.g. PydFactorValue-0001")
    _model = model.FactorValue

class PydSample(BaseModel):
    """Represents a Sample material in an experimental graph."""
    name : str = Field(..., description = "A name/reference for the sample material.")
    derives_from_uids : List[str] = Field(..., description = "A list of the source material (PydSource) that this sample is derived from. The PydSources that this PydSample derives from MUST be present in the same study. The strings in the list are the UIDs of the PydSource objects.")
    comments : List[PydComment] = Field(..., description = "Helpful comments to inform the experimenter about the specifics of the sample.")
    uid : str = Field(..., description = "An identifier for the sample that is unique across all objects types across the entire investigation. E.g. PydSample-0001")
    _model = model.Sample

class PydParameterValue(BaseModel):
    """A ParameterValue represents the instance value of a ProtocolParameter, used in a Process."""
    category : Optional[PydProtocolParameter] = Field(None, description = "A link to the relevant ProtocolParameter that the value is set for.")
    value : Optional[Union[str, int, float, PydOntologyAnnotation]] = Field(None, description = "The value of the parameter.")
    unit : Optional[PydOntologyAnnotation] = Field(None, description = "The qualifying unit classifier, if the value is numeric.")
    comments : Optional[List[PydComment]] = Field(None, description = "Comments associated with instances of this class.")
    uid : str = Field(..., description = "An identifier for the parameter value that is unique across all objects types across the entire investigation. E.g. PydParameterValue-0001")
    _model = model.ParameterValue

class PydDataFile(BaseModel):
    """Represents the data file output of an assay in the experimental graph. This is typically the file that is produced from an experimental assay or data collection from an instrument."""
    filename : str = Field(..., description = "A proposed name for the data file. The name should be descriptive and refer to the right file format. e.g. 'sample1.tar.gz' if the assay data collection process is expected to produce a tarball from sample1 or 'knockouts.csv' if the assay data collection process is expected to produce a CSV file from knockout data.")
    generated_from_uids : List[str] = Field(..., description = "A list of the samples (PydSample) that this data file is generated from. The PydSamples that this PydDataFile is generated from MUST be present in the same study. The strings in the list are the UIDs of the PydSample objects.")
    label : str = Field(..., description="""The type of the data file. MUST be one of the following choices (pick the most appropriate one given the nature of the assay): ['Raw Data File','Derived Data File','Image File','Acquisition Parameter Data File','Derived Spectral Data','Protein Assignment File','Raw Spectral Data File','Peptide Assignment File','Array Data File','Derived Array Data File','Post Translational Modification Assignment File','Derived Array Data Matrix File','Free Induction Decay Data File','Metabolite Assignment File','Array Data Matrix File']""")
    uid : str = Field(..., description = "An identifier for the data file that is unique across all objects types across the entire investigation. E.g. PydDataFile-0001")
    _model = model.DataFile

class PydProcess(BaseModel):
    """Process nodes represent the application of a protocol to some input material (e.g. a Source) to produce some output (e.g.a Sample) or a sample to produce a data file.
You MUST fill out the inputs and outputs, they cannot be empty lists."""
    name : str = Field(..., description = "If relevant, a unique name for the process to disambiguate it from other processes.")
    executes_protocol_uid : str = Field(..., description="A reference to the Protocol that this process executes. The string is the UID of the PydProtocol object.")
    inputs_uids : List[str] = Field(..., description = "A list of input sources consumed by the process. This CANNOT be an empty list. The strings in the list are the UIDs of the PydSource/PydSample objects.")
    outputs_uids : List[str] = Field(..., description = "A list of output samples produced by the process. This CANNOT be an empty list. The strings in the list are the UIDs of the PydSample/PydDataFile objects.")
    uid : str = Field(..., description = "An identifier for the process that is unique across all objects types across the entire investigation. E.g. PydProcess-0001")
    _model = model.Process

class PydAssay(BaseModel):
    """An Assay represents a test performed on samples that generates data files and describes the process by which this happens. 
When creating an assay, you MUST fill out the data_files and it cannot be an empty list."""
    technology_platform : str = Field(..., description = "Manufacturer and platform name, e.g. Bruker AVANCE.")
    technology_type_uid : str = Field(..., description = "The type of technology used in the assay. The string is the UID of the PydOntologyAnnotation object.")
    measurement_type_uid : str = Field(..., description="The type of measurement being made in this assay. The string is the UID of the PydOntologyAnnotation object.")
    data_files_uids : List[str] = Field(..., description = "Data files expected to be produced by the Assay. Each data file is a file produced when samples are measured or tested according to the assay's requirements. The strings in the list are the UIDs of the PydDataFile objects. The CANNOT be an empty list.")
    process_sequence_uids : List[str] = Field(..., description = "A list of Process objects mapping samples to data files. The data files are the files expected to be produced from the data collection process described by this assay. Every sample in the assay must appear in at least one process listed here. Each data file MUST come from at least one sample and every sample MUST map to at least one data source. The inputs and outputs of each process CANNOT BE EMPTY. The strings in the list are the UIDs of the PydProcess objects.")
    samples_uids : List[str] = Field(..., description = "Samples associated with the Assay. The strings in the list are the UIDs of the PydSample objects.")
    uid : str = Field(..., description = "An identifier for the assay that is unique across all objects types across the entire investigation. E.g. PydAssay-0001")
    _model = model.Assay

class PydStudy(BaseModel):
    """Study is the central unit, containing information on the subject under study, its characteristics and any treatments applied. 
When creating a Study, you MUST fill out the process_sequences and it cannot be an empty list."""
    title_ : str = Field(..., description = "A concise phrase used to encapsulate the purpose and goal of the study.")
    sources_uids : List[str] = Field(..., description = "Sources associated with the study. Each source refers to a biological source material. Multiple samples might be derived from a single source. The strings in the list are the UIDs of the PydSource objects.")
    samples_uids : List[str] = Field(..., description = "Samples associated with the study. Each sample should refer to an individual discrete sample that would be run through an experiment. The strings in the list are the UIDs of the PydSample objects.")
    process_sequence_uids : List[str] = Field(..., description = "A list of Process objects mapping sources to samples. Every source and sample MUST appear in at least one process listed here. Each sample MUST come from at least one source and every source MUST map to at least one sample. The inputs and outputs of each process CANNOT BE EMPTY. The strings in the list are the UIDs of the PydProcess objects.")
    protocols_uids : List[str] = Field(..., description = "A list of protocol objects describing experimental procedures used in this study. The strings in the list are the UIDs of the PydProtocol objects.")
    assays_uids : List[str] = Field(..., description = "A list of assay objects describing the data collection processes used in this study. The strings in the list are the UIDs of the PydAssay objects.")
    uid : str = Field(..., description = "An identifier for the study that is unique across all objects types across the entire investigation. E.g. PydStudy-0001")
    comments : List[PydComment] = Field(..., description = "Comments to explain in more detail the specifics of this study.")
    _model =  model.Study

class PydInvestigationDraft(BaseModel):
    """Contains all the information and components in the design of a scientific investigation to test a hypothesis. An investigation contains studies that themselves contain assays. Studies involve deriving biological samples from sources and assays generate data from those samples. All components and fields for the investigation must be COMPLETELY defined here."""
    title_ : str = Field(..., description = "The investigation's concise but informative title")
    description : str = Field(..., description = "A free-text description of the investigation.")
    protocol_types : List[PydOntologyAnnotation] = Field(..., description = "A list of ontology annotation term objects that are used to classify the types of protocols used in this investigation.")
    measurement_types : List[PydOntologyAnnotation] = Field(..., description="A list of ontology annotation term objects that are used to classify the type of measurements being made in this investigation's assays.")
    sources : List[PydSource] = Field(..., description = "A list of source objects describing the biological material used in the investigation.")
    samples : List[PydSample] = Field(..., description = "A list of sample objects describing the biological material used in the investigation.")
    executes_protocols : List[PydProtocol] = Field(..., description="A list of protocol objects describing experimental procedures used in this investigation. Make sure to define and list ALL the protocols that will be needed.")
    process_sequences : List[PydProcess] = Field(..., description = "A list of process objects either mapping sources to samples (for studies) or samples to data files (for assays). Every source and sample MUST appear in at least one process listed here. Each sample MUST come from at least one source and every source MUST map to at least one sample. Every sample in the assay must appear in at least one listed assay process. Each data file MUST come from at least one sample and every sample MUST map to at least one data source. The inputs and outputs of each process CANNOT BE EMPTY")
    technology_types : List[PydOntologyAnnotation] = Field(..., description = "A list of technology types used in the investigation.")
    uid : str = Field(..., description = "An identifier for the investigation that is unique across all objects types across the entire investigation. E.g. PydInvestigation-0001")
    _model =  model.Investigation

class PydInvestigationRevised(PydInvestigationDraft):
    """The filled-out plan for an investigation that includes the plans for assays and studies. This is the final version of the investigation plan."""
    data_files : List[PydDataFile] = Field(..., description = "Data files that are expected to be produced by assays in the study. Each data file is a file produced when samples are measured or tested according to the assay's requirements. The CANNOT be an empty list.")
    assays : List[PydAssay] = Field(..., description = "An Assay represents the portion of the experimental design that involves data collection (e.g. getting data from samples via some measurement or instrument process)")
    studies : List[PydStudy] = Field(..., description = "A list of studies. Studies are the central units of scientific investigations. They contain information on the plan for investigating the subject in question. You MUST populate this list with at least one study.")
    _model =  model.Investigation


async def main():
    parser = argparse.ArgumentParser(description='Generate an investigation')
    parser.add_argument('--suggested_study_json', type = str, required = True, help = 'A json file containing a serialized study suggestion')
    parser.add_argument('--out_dir', type=str, help='The directory to save the investigation to', default = 'investigation')
    # parser.add_argument('--hypothesis', type = str, help = 'The hypothesis to test', required = True)
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok = True)

    investigation_creator = Role(
            name = "investigation_creator",
            instructions ="You are a scientist that specializes in compiling protocols for laboratory experimenters to perform. You are extremely detail-oriented and read directions carefully. Read the requirements for each field and follow them exactly when generating output.",
            constraints=None,
            register_default_events=True,
            model="gpt-4-turbo-preview"
        )

    request = f"""Take the suggested study and turn in into a fully-specific investigation. You are being asked to create an investigation draft which contains ALL the components you'll need to test the hypothesis.
    Note that each assay will ultimately be assigned a single `measurement_type` (from `measurement_types`) and `technology_type` (from `technology_types`) pair. You MUST ensure that every assay's (measurement_type, technology_type) term pair is one of these (picking the most appropriate AND being case-sensitive): [(metabolite profiling,NMR spectroscopy),(targeted metabolite profiling,NMR spectroscopy),(untargeted metabolite profiling,NMR spectroscopy),(isotopomer distribution analysis,NMR spectroscopy),(metabolite profiling,mass spectrometry),(targeted metabolite profiling,mass spectrometry),(untargeted metabolite profiling,mass spectrometry),(isotologue distribution analysis,mass spectrometry),(transcription profiling,DNA microarray),(genotype profiling,DNA microarray),(epigenome profiling,DNA microarray),(exome profiling,DNA microarray),(DNA methylation profiling,DNA microarray),(copy number variation profiling,DNA microarray),(transcription factor binding site identification,DNA microarray),(protein-DNA binding site identification,DNA microarray),(SNP analysis,DNA microarray),(transcription profiling,nucleic acid sequencing),(transcription factor binding site identification,nucleic acid sequencing),(protein-DNA binding site identification,nucleic acid sequencing),(DNA methylation profiling,nucleic acid sequencing),(histone modification profiling,nucleic acid sequencing),(genome sequencing,nucleic acid sequencing),(metagenome sequencing,nucleic acid sequencing),(environmental gene survey,nucleic acid sequencing),(cell sorting,flow cytometry),(cell counting,flow cytometry),(cell migration assay,microscopy imaging),(phenotyping,imaging),(transcription profiling,RT-pcr)]
    """

    suggested_study = SuggestedStudy(**json.loads(open(args.suggested_study_json).read()))
    investigation_draft = await investigation_creator.aask([request, suggested_study], PydInvestigationDraft)
    
    # request = f"""Design an investigation to test the following hypothesis provided below. You are being asked to create an investigation draft which contains ALL the components you'll need to test the hypothesis. 
    # Note that each assay will ultimately be assigned a single `measurement_type` (from `measurement_types`) and `technology_type` (from `technology_types`) pair. You MUST ensure that every assay's (measurement_type, technology_type) term pair is one of these (picking the most appropriate AND being case-sensitive): [(metabolite profiling,NMR spectroscopy),(targeted metabolite profiling,NMR spectroscopy),(untargeted metabolite profiling,NMR spectroscopy),(isotopomer distribution analysis,NMR spectroscopy),(metabolite profiling,mass spectrometry),(targeted metabolite profiling,mass spectrometry),(untargeted metabolite profiling,mass spectrometry),(isotologue distribution analysis,mass spectrometry),(transcription profiling,DNA microarray),(genotype profiling,DNA microarray),(epigenome profiling,DNA microarray),(exome profiling,DNA microarray),(DNA methylation profiling,DNA microarray),(copy number variation profiling,DNA microarray),(transcription factor binding site identification,DNA microarray),(protein-DNA binding site identification,DNA microarray),(SNP analysis,DNA microarray),(transcription profiling,nucleic acid sequencing),(transcription factor binding site identification,nucleic acid sequencing),(protein-DNA binding site identification,nucleic acid sequencing),(DNA methylation profiling,nucleic acid sequencing),(histone modification profiling,nucleic acid sequencing),(genome sequencing,nucleic acid sequencing),(metagenome sequencing,nucleic acid sequencing),(environmental gene survey,nucleic acid sequencing),(cell sorting,flow cytometry),(cell counting,flow cytometry),(cell migration assay,microscopy imaging),(phenotyping,imaging),(transcription profiling,RT-pcr)]

    # # hypothesis:\n`{args.hypothesis}`"""
    # investigation_draft = await investigation_creator.aask(request, PydInvestigationDraft)
    
    
    pkl.dump(investigation_draft, open(os.path.join(args.out_dir, 'investigation.pkl'), 'wb'))
    with open(os.path.join(args.out_dir,"investigation_draft.json"), "w") as f:
        print(json.dumps(investigation_draft.dict(), indent = 4), file = f)
    # update_request = f"""You were asked to design an investigation to test the hypothesis `{args.hypothesis}`. Following this message is your initial plan. Take this plan and create a finalized investigation. You MUST fill out the `studies` and `assays`"""
    update_request = f"""You were asked to design an investigation that specifies the components needed to carry out the suggested study below. Following this message is your initial plan. Take this plan and create a finalized investigation. You MUST fill out the `studies` and `assays`
    
    Suggested Study: {suggested_study.dict()}
    """
    investigation = await investigation_creator.aask([update_request, investigation_draft], PydInvestigationRevised)
    pkl.dump(investigation, open(os.path.join(args.out_dir, 'investigation_final.pkl'), 'wb'))
    with open(os.path.join(args.out_dir,"investigation_final.json"), "w") as f:
        print(json.dumps(investigation.dict(), indent = 4), file = f)


    model_investigation_instance, uid_isa = initialize_models(investigation)
    out_json = os.path.join(args.out_dir, "isa_investigation.json")
    with open(out_json, "w") as f:
        print(json.dumps(model_investigation_instance, cls=isajson.ISAJSONEncoder, sort_keys=True, indent=4, separators=(',', ': ')), file = f)
    with open(out_json, 'r') as f:
        report = isajson.validate(f)
    print(report)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()