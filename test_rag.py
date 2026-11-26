
from backend.services.rag_service import answer_question

question = "How does machine learning help businesses?"

result = answer_question(question)

print("\nQuestion:", result["question"])
print("\nAI Answer:", result["answer"])
print("\nSources:")

for source in result["sources"]:
    print(source)
