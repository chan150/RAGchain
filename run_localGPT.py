import pinecone
from langchain.chains import RetrievalQA
# from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.vectorstores import Chroma, Pinecone
from langchain.embeddings import HuggingFaceInstructEmbeddings
from langchain.llms import HuggingFacePipeline
from constants import CHROMA_SETTINGS, PERSIST_DIRECTORY, PINECONE_TOKEN, PINECONE_ENV
import click

from constants import CHROMA_SETTINGS

quantized_model_dir = "../llama.cpp/models/ko_alapca_polyglot/gptq_4bit" # TODO : set your quantized model path
tokenizer_dir = "qwopqwop/KoAlpaca-Polyglot-12.8B-GPTQ"

# def load_model():
#     """
#     Select a model on huggingface.
#     If you are running this for the first time, it will download a model for you.
#     subsequent runs will use the model from the disk.
#     """
#     model_id = "TheBloke/vicuna-7B-1.1-HF"
#     tokenizer = LlamaTokenizer.from_pretrained(model_id)
#
#     model = LlamaForCausalLM.from_pretrained(model_id,
#                                              #   load_in_8bit=True, # set these options if your GPU supports them!
#                                              #   device_map=1#'auto',
#                                              #   torch_dtype=torch.float16,
#                                              #   low_cpu_mem_usage=True
#                                              )
#
#     pipe = pipeline(
#         "text-generation",
#         model=model,
#         tokenizer=tokenizer,
#         max_length=2048,
#         temperature=0,
#         top_p=0.95,
#         repetition_penalty=1.15
#     )
#
#     local_llm = HuggingFacePipeline(pipeline=pipe)
#
#     return local_llm


def load_model(device: str):
    try:
        from auto_gptq import AutoGPTQForCausalLM
        from transformers import AutoTokenizer, TextGenerationPipeline, BitsAndBytesConfig, AutoModelForCausalLM
        import torch
    except ImportError:
        raise ModuleNotFoundError(
            "Could not import AutoGPTQ library. "
            "Please install the AutoGPTQ library to "
            "use this embedding model: pip install auto-gptq"
        )
    except Exception:
        raise NameError(f"Could not load quantized model from path: {quantized_model_dir}")

    # model = AutoGPTQForCausalLM.from_quantized(quantized_model_dir, device="cuda:0")
    # tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir)

    if device == "cuda" :
        model_id = "beomi/polyglot-ko-12.8b-safetensors"  # safetensors 컨버팅된 레포
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )

        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_config, device_map={"": 0})
        pipeline = TextGenerationPipeline(model=model, tokenizer=tokenizer)
        return HuggingFacePipeline(pipeline=pipeline)

# @click.command()
# @click.option('--device_type', default='gpu', help='device to run on, select gpu or cpu')
# def main(device_type, ):
#     # load the instructorEmbeddings
#     if device_type in ['cpu', 'CPU']:
#         device='cpu'
#     else:
#         device='cuda'
 
    
 ## for M1/M2 users:

@click.command()
@click.option('--device_type', default='cuda', help='device to run on, select gpu, cpu or mps')
def main(device_type, ):
    # load the instructorEmbeddings
    if device_type in ['cpu', 'CPU']:
        device='cpu'
    elif device_type in ['mps', 'MPS']:
        device='mps'
    else:
        device='cuda'

    print(f"Running on: {device}")

    embeddings = HuggingFaceInstructEmbeddings(model_name = "BM-K/KoSimCSE-roberta-multitask", model_kwargs={"device": device})
    # load the vectorstore
    # db = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings, client_settings=CHROMA_SETTINGS)
    pinecone.init(api_key=PINECONE_TOKEN, environment=PINECONE_ENV)
    index_name = "localgpt-demo"
    db = Pinecone.from_existing_index(index_name, embeddings)
    retriever = db.as_retriever()
    # Prepare the LLM
    # callbacks = [StreamingStdOutCallbackHandler()]
    # load the LLM for generating Natural Language responses. 
    llm = load_model()
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True)
    # Interactive questions and answers
    while True:
        query = input("\nEnter a query: ")
        if query == "exit":
            break

        # Get the answer from the chain
        res = qa({"query": query})
        answer, docs = res['result'], res['source_documents']

        # Print the result
        print("\n\n> Question:")
        print(query)
        print("\n> Answer:")
        print(answer)

        # # Print the relevant sources used for the answer
        print("----------------------------------SOURCE DOCUMENTS---------------------------")
        for document in docs:
            print("\n> " + document.metadata["source"] + ":")
            print(document.page_content)
        print("----------------------------------SOURCE DOCUMENTS---------------------------")


if __name__ == "__main__":
    main()
