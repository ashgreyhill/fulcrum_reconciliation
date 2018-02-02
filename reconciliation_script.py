from .classes import AutoReconciler
import os
import dotenv

# Load in any environment variables
env_path = os.path.join(os.getcwd(), '.env')
dotenv.load_dotenv(env_path)

# Set authorization key value for request headers
API_KEY = os.environ.get('FULCRUM_SANDBOX_API_KEY')

auto_reconciler = AutoReconciler(API_KEY)

auto_reconciler.reconcile_completed_surveys()

print('Finished')
