from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler
from django_apscheduler.jobstores import DjangoJobStore
from carrierservice.models import Package
from carrierservice.views import get_tracking_status
from carrierservice.services.llm import generate_mail
from carrierservice.services.mail_sender import send_status_email

def check_status_job():
    packages = Package.objects.all()
    for package in packages:
        try:
            api_data = get_tracking_status(package.tracking_number)
            new_status = api_data.get("status", {}).get("statusCode") 
            
            if new_status and new_status != package.package_status:
                email_content = generate_mail(api_data)
                if package.email:
                    send_status_email(
                        to_email=package.email,
                        subject=f"Update on your package: {package.tracking_number}",
                        body_text=email_content
                    )
                package.package_status = new_status
                package.save()
                print(f"Updated and sent email for {package.tracking_number}: {new_status}")
        except Exception as e:
            print(f"Error checking package {package.tracking_number}: {str(e)}")

class Command(BaseCommand):
    help = "Starts the background worker to poll DHL API for package updates."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone='UTC')
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            check_status_job,
            "interval",
            minutes=30,
            id="check_package_status",
            replace_existing=True
        )

        self.stdout.write("Starting tracking worker... Press Ctrl+C to exit.")
        try:
            scheduler.start()
        except KeyboardInterrupt:
            self.stdout.write("Worker stopped.")
