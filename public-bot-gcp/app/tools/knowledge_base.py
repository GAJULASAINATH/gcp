from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class KnowledgeBaseTool:
    def __init__(self, db_session):
        self.db = db_session

    async def search(self, agent_id: str, query: str):
        """
        Fetches the FULL Knowledge Base for the agent.
        We let the AI filter relevance instead of SQL.
        """
        context_parts = []
        
        try:
            # 1. Fetch ALL FAQs for this Agent
            # FAQs are short, so we can usually afford to load all of them.
            faq_query = text("""
                SELECT question, answer 
                FROM knowledge_base_faqs 
                WHERE agent_id = :agent_id 
            """)
            faq_res = await self.db.execute(faq_query, {"agent_id": agent_id})
            
            faqs = faq_res.mappings().all()
            if faqs:
                context_parts.append("## FREQUENTLY ASKED QUESTIONS (FAQs)")
                for row in faqs:
                    context_parts.append(f"Q: {row['question']}\nA: {row['answer']}")
                context_parts.append("-" * 20)

            # 2. Fetch Documents (With Limit)
            # We fetch all docs but limit the character count per doc to avoid exploding tokens.
            doc_query = text("""
                SELECT title, content 
                FROM knowledge_base_documents 
                WHERE agent_id = :agent_id 
            """)
            doc_res = await self.db.execute(doc_query, {"agent_id": agent_id})
            
            docs = doc_res.mappings().all()
            if docs:
                context_parts.append("## COMPANY DOCUMENTS & POLICIES")
                for row in docs:
                    # Truncate massive docs to first 3000 chars to be safe
                    content_preview = row['content'][:3000] 
                    context_parts.append(f"DOCUMENT TITLE: {row['title']}\nCONTENT:\n{content_preview}")

            if not context_parts:
                return None
            
            # Combine everything into one big text block for the AI
            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"KB Fetch Error: {e}")
            return None