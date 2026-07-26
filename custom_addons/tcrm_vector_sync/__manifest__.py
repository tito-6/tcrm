{
    'name': 'TCRM Vector Sync',
    'version': '1.0',
    'category': 'Productivity',
    'summary': 'Real-time vectorization: sync TCRM records to remote RAG/vector store',
    'description': """
TCRM Vector Sync
================
- Abstract mixin tcrm.vector.sync.mixin for models that should be vectorized.
- Overrides create(), write(), unlink() to enqueue payloads to tcrm.vector.sync.queue.
- Cron processes the queue and POSTs to {tcrm.ai_base_url}/ingest.
- Extends res.partner with the mixin and semantic text for search.
    """,
    'author': 'TCRM',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/vector_sync_cron.xml',
    ],
    'external_dependencies': {'python': ['requests']},
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
