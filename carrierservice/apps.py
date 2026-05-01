from django.apps import AppConfig
import os
import threading

class CarrierserviceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'carrierservice'

    def ready(self):
        # Prevent starting twice if using Django's auto-reloader
        if os.environ.get('RUN_MAIN') == 'true':
            # We start the worker in a separate thread so it doesn't block the server
            thread = threading.Thread(target=self.start_worker)
            thread.daemon = True
            thread.start()

    def start_worker(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        from django_apscheduler.jobstores import DjangoJobStore
        from carrierservice.management.commands.start_worker import check_status_job

        # Use BackgroundScheduler so it doesn't block
        scheduler = BackgroundScheduler(timezone='UTC')
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Add the job
        scheduler.add_job(
            check_status_job,
            "interval",
            minutes=30, # Default to 30 mins for production feel
            id="check_package_status",
            replace_existing=True
        )

        print("--- Background Worker Started Automatically ---")
        try:
            scheduler.start()
        except Exception as e:
            print(f"Error starting background worker: {e}")
