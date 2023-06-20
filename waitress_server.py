from waitress import serve
import start_mqi_framework
serve(start_mqi_framework.app, host='0.0.0.0', port=80)

