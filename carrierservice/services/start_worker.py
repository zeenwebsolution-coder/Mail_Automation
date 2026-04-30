from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler
from django_apscheduler.jobstores import DjangoJobStore
from carrierservice.models import Package
from carrierservice.views import get_tracking_status
from carrierservice.llm import generate_mail
from carrierservice.utils import send_status_email

class Command(BaseCommand):
    help = "Starts the background worker to poll DHL API for package updates."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone='UTC')
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # This job will run every 30 minutes. Adjust 'minutes' as needed.
        @scheduler.scheduled_job("interval", minutes=30, id="check_package_status", replace_existing=True)
        def check_status_job():
            packages = Package.objects.all()
            for package in packages:
                try:
                    # 1. Fetch current status from API
                    # (Note: make sure get_tracking_status returns exactly what you expect)
                    api_data = get_tracking_status(package.tracking_number)
                    
                    # You might need to adjust this key based on the actual DHL API response JSON structure
                    new_status = api_data.get("status", {}).get("statusCode") 
                    
                    if new_status and new_status != package.package_status:
                        # 2. Status has changed! Generate Email Content using LLM
                        email_content = generate_mail(api_data)
                        
                        # 3. Send the Email via Mailjet
                        if package.customer_email:
                            send_status_email(
                                to_email=package.customer_email,
                                subject=f"Update on your package: {package.tracking_number}",
                                body_text=email_content
                            )
                        
                        # 4. Update the database with the new status so we don't send duplicates
                        package.package_status = new_status
                        package.save()
                        
                        print(f"Updated and sent email for {package.tracking_number}: {new_status}")
                except Exception as e:
                    print(f"Error checking package {package.tracking_number}: {str(e)}")

        self.stdout.write("Starting tracking worker... Press Ctrl+C to exit.")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            self.stdout.write("Worker stopped.")

