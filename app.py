import API
from flask_sqlalchemy import SQLAlchemy

app = API.create_app()

if __name__ == "__main__":
   app.run(debug=True, threaded=True)





