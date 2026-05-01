from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler
from django_apscheduler.jobstores import DjangoJobStore
from carrierservice.models import Package
from carrierservice.views import get_tracking_status
from carrierservice.services.llm import generate_mail
from carrierservice.services.mail_sender import send_status_email
from tenacity import retry, stop_after_attempt, wait_exponential

class Command(BaseCommand):
    help = "Starts the background worker to poll DHL API for package updates."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone='UTC')
        scheduler.add_jobstore(DjangoJobStore(), "default")

        @scheduler.scheduled_job("interval", minutes=1, id="check_package_status", replace_existing=True)
        def check_status_job():
            print("--- Worker Heartbeat: Searching for due packages... ---", flush=True)
            from django.utils import timezone
            from datetime import timedelta
            from django.core.cache import cache
            
            # Find packages that haven't been updated in the last 30 minutes
            thirty_mins_ago = timezone.now() - timedelta(minutes=30)
            packages_due = Package.objects.filter(updated_at__lte=thirty_mins_ago)
            print(f"Found {packages_due.count()} packages due for update.", flush=True)
            
            for package in packages_due:
                try:
                    # 1. Check Cache first
                    cache_key = f"status_{package.tracking_number}"
                    cached_status = cache.get(cache_key)
                    
                    # 2. Fetch current status from API
                    api_data = get_tracking_status(package.tracking_number)
                    
                    new_status = None
                    if "shipments" in api_data and len(api_data["shipments"]) > 0:
                        new_status = api_data["shipments"][0].get("status", {}).get("status")
                    
                    if new_status:
                        # Use cached status for comparison if DB is not updated yet
                        current_ref_status = cached_status or package.package_status
                        
                        if new_status != current_ref_status:
                            # 3. Status has changed! Generate Email (JSON Format)
                            mail_data = generate_mail(api_data)
                            new_summary = mail_data.get("body", "")
                            
                            # 4. Send the Email via Mailjet
                            if package.email:
                                send_status_email(
                                    to_email=package.email,
                                    subject=mail_data.get("subject", "Package Update"),
                                    body_text=new_summary
                                )
                            
                            package.package_status = new_status
                            package.agent_summary = new_summary # Save the new summary to the DB
                            # Update cache
                            cache.set(cache_key, new_status, timeout=3600)
                        
                        # 5. Always update the timestamp so it resets the 30-minute timer
                        package.save() 
                        print(f"Staggered update for {package.tracking_number}: {new_status}", flush=True)
                except Exception as e:
                    print(f"Error checking package {package.tracking_number}: {str(e)}", flush=True)

        # Run the check immediately on startup
        self.stdout.write("Running initial package check...")
        check_status_job()

        self.stdout.write("Starting tracking worker scheduler... Press Ctrl+C to exit.")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            self.stdout.write("Worker stopped.")

