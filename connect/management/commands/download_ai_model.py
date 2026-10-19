"""
Download the local model and run one search with it, before the first web request.

    python manage.py download_ai_model

The first "Ask in plain English" search (/search/ask/) downloads the weights by
itself. This command does it ahead of time, so that first search is not the one
that waits, and shows the model answering. The weights go into the Hugging Face
cache (~/.cache/huggingface), never into this repository.
"""

import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from connect import ai_search

SAMPLE = "shy art lovers free on Sunday morning"


class Command(BaseCommand):
    help = "Download the local model (settings.AI_LOCAL_MODEL) and run one test search."

    def handle(self, *args, **options):
        if not settings.AI_LOCAL_ENABLED:
            raise CommandError("AI_LOCAL_ENABLED=0 in .env: the local model is switched off.")
        self.stdout.write(f"Model: {settings.AI_LOCAL_MODEL} (downloads once, then loads from the cache)")
        interests, colleges = ai_search.vocabulary()
        started = time.perf_counter()
        try:
            reply = ai_search.generate_reply(ai_search.build_messages(SAMPLE, interests, colleges))
        except ai_search.ModelUnavailable as error:
            raise CommandError(str(error)) from error
        filters = ai_search.clean_filters(ai_search.first_json_object(reply), interests, colleges)
        self.stdout.write(f"Loaded and answered in {time.perf_counter() - started:.1f} s.")
        self.stdout.write(f"Request:  {SAMPLE}\nReply:    {reply.strip()}\nFilters:  {filters}")
        if not filters:
            raise CommandError("The model answered, but nothing usable came out of it.")
        self.stdout.write(self.style.SUCCESS("The local model is ready."))
