# Model Card — PawPal+ AI System

**Project:** PawPal+ — AI-Powered Pet Care Management System  
**Base project:** PawPal+ (Modules 1-3)  
**AI feature added:** Retrieval-Augmented Generation (RAG)  
**Model used:** OpenAI GPT-3.5-turbo (generation) + all-MiniLM-L6-v2 (embedding)

---

## Intended Use

PawPal+ is designed to help pet owners manage daily care routines and get quick, document-grounded answers to common pet care questions. It is not a veterinary tool and should not be used to diagnose illness, replace professional veterinary advice, or make decisions about pet medications.

---

## Limitations and Potential Biases

**Knowledge base coverage:** The system only knows what is in the four `.txt` documents in the `/docs` folder. Any pet species, condition, or care practice not covered there will either produce a low-confidence warning or no useful answer. The current knowledge base covers dogs, cats, nutrition, and general health tips. It does not cover birds, reptiles, rabbits, fish, or exotic pets.

**Species bias:** The source documents focus heavily on dogs and cats. A question about a rabbit's dental care will likely return low-confidence results because the documents do not cover it. This is correct behavior for the system, but it does mean the app is not equally useful for all pet owners.

**Hallucination risk:** GPT-3.5-turbo can still produce plausible-sounding but incorrect answers even when told to stay within the provided context. The system prompt restricts this as much as possible, but it cannot be fully eliminated. The guardrails layer partially mitigates this by flagging low-confidence responses before they are shown to users.

**Temporal bias:** The documents were written at a fixed point in time. Veterinary recommendations change over time, including vaccination schedules, dietary advice, and parasite control products. The knowledge base needs periodic human review to stay accurate.

---

## Misuse Potential and Prevention

**Risk 1 — Medical decisions:** A user might try to use AI-generated advice to avoid taking a sick pet to the vet. To address this, every response instructs users to consult a vet for medical concerns, and the guardrails block responses that suggest giving medication without professional oversight.

**Risk 2 — Dangerous medication prompts:** A user could ask whether human medications are safe for pets. The guardrails module contains a pattern list that blocks any response mentioning ibuprofen, aspirin, acetaminophen, or similar substances in the context of giving them to pets.

**Risk 3 — Overconfidence:** A user might trust a high-confidence answer too literally. To address this, confidence scores are shown visually for every response, and any answer generated without retrieved context receives an explicit low-confidence disclaimer.

---

## Testing Results and What Surprised Me

Running the evaluation harness across 8 predefined cases produced 8/8 correct results. All safety cases involving dangerous medication prompts were blocked correctly.

The most surprising finding during testing was how often valid answers received a low-confidence flag just because the phrasing of the question did not closely match the wording in the source documents. For example, "signs of dental disease in dogs" retrieved strong results, but "what does bad dental health look like in a dog" retrieved fewer chunks. The semantic intent was the same but the surface wording was different enough to affect retrieval quality. This is a real limitation of semantic search that I did not fully appreciate before building this.

A second unexpected issue came up with guardrail pattern matching. A sentence that read "there is no need to see a vet immediately for minor scratches" was caught by the `no need.*vet` pattern and incorrectly blocked. I had to refine the regex to `no need to see a vet` to make it more specific and avoid blocking legitimate advice.

---

## AI Collaboration During This Project

### Helpful AI suggestion
When designing the chunking strategy for the RAG pipeline, I asked for suggestions on how to split the documents. The recommendation to use overlapping windows (250-word chunks with 50-word overlap) was helpful right away. It stopped important context from being cut off at chunk boundaries and improved retrieval relevance compared to splitting without overlap.

### Flawed AI suggestion
When I asked for guardrail pattern suggestions, the initial regex set included a very broad pattern: `\bno\s+vet\b`. This would have blocked any response containing the phrase "no vet appointment needed" even in cases where that was completely appropriate advice, like for routine grooming questions. I had to manually rewrite this to a more specific pattern that only matched direct safety-critical phrasings. AI-generated regex patterns need careful human review before being used in a safety context.

---

## Reflection on Being the Lead Architect

Building a complete AI system involved a lot more than calling an API. I had to design the data flow, test the failure cases, and decide where human judgment needed to stay in the loop. The AI was useful for generating boilerplate, suggesting algorithms, and drafting documentation. But the important design decisions required me to think carefully: where to set the confidence threshold, which content to block in guardrails, what the system should say when it does not know something, and when to tell a user to see a professional instead of answering. Those decisions cannot be handed off to the AI. That is what being the architect actually means.