# AWS Elastic Beanstalk entry point
from app import create_app

application = create_app()

if __name__ == "__main__":
    application.run()
