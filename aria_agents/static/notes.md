
```
    """Generate an investigation from a suggested study"""
        pre_session = current_session.get()
        session_id = pre_session.id if pre_session else str(uuid.uuid4())

        if data_store is None:
            project_folders = os.environ.get("PROJECT_FOLDERS", "./projects")
            project_folder = os.path.abspath(
                os.path.join(project_folders, project_name)
            )
            event_bus = None
        else:
            event_bus = data_store.get_event_bus()

        if data_store is None:
            # Load the suggested study from a JSON file
            suggested_study_file = os.path.join(
                project_folder, "suggested_study.json"
            )
            with open(suggested_study_file, encoding="utf-8") as ss_file:
                suggested_study = SuggestedStudy(**json.load(ss_file))

            # Set the query index directory to the project folder
            query_index_dir = os.path.join(project_folder, "query_index")
        else:
            # Find a better way to get the suggested study from the datastore
            for obj in data_store.storage.values():
                if obj["name"] == f"{project_name}:suggested_study.json":
                    # Load the suggested study from the HyphaDataStore
                    suggested_study = SuggestedStudy(**obj["value"])
                if obj["name"] == f"{project_name}:pubmed_index_dir":
                    # Set the query index directory to the project folder
                    query_index_dir = obj["value"]
```

```
 """Searches PubMed Central using `PMCQuery` and creates a citation query engine."""
        loader = PubmedReader()
        terms = urllib.parse.urlencode({"term": pmc_query.query, "db": "pmc"})
        print(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{terms}"
        )
        # print(test_pmc_query_hits(pmc_query))
        documents = loader.load_data(
            search_query=pmc_query.query,
            max_results=CONFIG["aux"]["paper_limit"],
        )
        if len(documents) == 0:
            return "No papers were found in the PubMed Central database for the given query. Please try different terms for the query."
        Settings.llm = OpenAI(model=CONFIG["llm_model"])
        Settings.embed_model = OpenAIEmbedding(
            model=CONFIG["aux"]["embedding_model"]
        )
        query_index = VectorStoreIndex.from_documents(documents)

        # Save the query index to disk
        query_index_dir = os.path.join(project_folder, "query_index")
        query_index.storage_context.persist(query_index_dir)
        if data_store is not None:
            project_name = os.path.basename(project_folder)
            data_store.put(
                obj_type="file",
                value=query_index_dir,
                name=f"{project_name}:pubmed_index_dir",
            )

        # Create a citation query engine object
        context["query_engine"] = CitationQueryEngine.from_args(
            query_index,
            similarity_top_k=CONFIG["aux"]["similarity_top_k"],
            citation_chunk_size=CONFIG["aux"]["citation_chunk_size"],
        )
        return f"Pubmed corpus with {len(documents)} papers has been created."
```

ArtifactManager:

```
async def get_dir(self, file_prefix, local_path):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self.session_id, "Please set session_id using `set_session_id()` before using artifact manager"
        dir_files = await self.list_dir(file_prefix)
        for dir_file in dir_files:
            file_content = await self.get(dir_file.path)
            local_path = os.path.join(local_path, dir_file.name)
            
            async with aiofiles.open(local_path, 'wb') as local_file:
                await local_file.write(file_content)


async def put_dir(self, local_path, file_prefix=None):
        assert self._svc, "Please call `setup()` before using artifact manager"
        assert self.session_id, "Please set session_id using `set_session_id()` before using artifact manager"
        for filename in os.listdir(local_path):
            file_path = os.path.join(local_path, filename)
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
                await self.put(
                    value=file_content,
                    name=filename
                )
                
async def list_dir(self, file_prefix):
    assert self._svc, "Please call `setup()` before using artifact manager"
    assert self.session_id, "Please set session_id using `set_session_id()` before using artifact manager"
    all_files = await self._svc.list_files(f"{self._prefix}/{self.session_id}")
    
    def file_has_prefix(this_file):
        return this_file.name.startswith(file_prefix)
    
    return list(filter(file_has_prefix, all_files))

```
