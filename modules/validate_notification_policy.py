from rdflib import *
from datetime import datetime
from dateutil import parser
import smtplib
import os
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


class ValidateNotificationPolicy:

    def __init__(self, graph_file, user_id):
        self.user_id = user_id
        self.graph_file = graph_file
        self.user_graph = Dataset()
        self.user_graph.parse(graph_file, format="trig")
        self.detection_period = self.get_detection_period()
        print(self.detection_period)
        exit()
        self.changes_count = self.get_changes_count()
        self.notification_thresholds = self.get_notification_thresholds()
        self.validate_policy()
        self.user_email = self.get_user_email()

    def get_detection_period(self):
        return "shshs"

    def get_changes_count(self):
        # query to get notification thresholds
        query = """
        PREFIX changes-graph: <http://www.example.com/changesGraph/user/>
        PREFIX notification-graph: <http://www.example.com/notificationGraph/user/>
        PREFIX contact-graph: <http://www.example.com/contactDetailsGraph/user/>
        PREFIX cdo: <https://change-detection-ontology.adaptcentre.ie/#>
        PREFIX rei-constraint: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiConstraint.owl#>
        PREFIX rei-policy: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiPolicy.owl#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        
        # GET COUNT FOR EACH CHANGE TYPE
        SELECT ?changeType (count(?change) AS ?count)
        WHERE
        {
          # QUERY USER GRAPH
          GRAPH changes-graph:2 {
            # GET DIFFERENT CHANGE TYPES
            VALUES ?changeType
            {
                       cdo:InsertSourceData
                       cdo:DeleteSourceData
                       cdo:MoveSourceData
                       cdo:UpdateSourceData
                       cdo:MergeSourceData
                       cdo:DatatypeSourceData
                     }
                    # GET EACH CHANGE FROM LOG
                     ?changeLog a cdo:ChangeLog ;
                                cdo:hasChange ?change.
                     ?change a ?changeType
          }
        }
        GROUP BY ?changeType
        """

        qres = self.user_graph.query(query)
        # count of each change type within graph
        change_type_counts = {}
        for (change_type, count) in qres:
            change_type_counts[change_type] = count.value
        return change_type_counts

    def get_notification_thresholds(self):
        # query to find thresholds within notification policy
        query = """
        PREFIX changes-graph: <http://www.example.com/changesGraph/user/>
        PREFIX notification-graph: <http://www.example.com/notificationGraph/user/>
        PREFIX contact-graph: <http://www.example.com/contactDetailsGraph/user/>
        PREFIX cdo: <https://change-detection-ontology.adaptcentre.ie/#>
        PREFIX rei-constraint: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiConstraint.owl#>
        PREFIX rei-policy: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiPolicy.owl#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        
        SELECT ?changeType ?threshold
        WHERE
        {
          # QUERY NOTIFICATION GRAPH
          GRAPH notification-graph:%s  {
            # GET THRESHOLD FOR EACH CHANGE TYPE
            ?constraint a rei-constraint:SimpleConstraint;
               rei-constraint:subject ?changeType;
               rei-constraint:object ?threshold .
          }
        }
        """ % (self.user_id)

        qres = self.user_graph.query(query)
        # notification threshold for each change type
        notification_thresholds = {}
        for row in qres:
            notification_thresholds[row[0]] = row[1]
        return notification_thresholds

    def get_user_email(self):
        # query to find thresholds within notification policy
        query = """
            PREFIX changes-graph: <http://www.example.com/changesGraph/user/>
            PREFIX notification-graph: <http://www.example.com/notificationGraph/user/>
            PREFIX contact-graph: <http://www.example.com/contactDetailsGraph/user/>
            PREFIX cdo: <https://change-detection-ontology.adaptcentre.ie/#>
            PREFIX rei-constraint: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiConstraint.owl#>
            PREFIX rei-policy: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiPolicy.owl#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            
            
            SELECT ?email
            WHERE
            {
              # QUERY CONTACT GRAPH
              GRAPH contact-graph:%s  {
                # GET EMAIL FOR USER WITH ID "1"
                ?user a foaf:Person;
                      foaf:mbox ?email .
              }
            }
        """ % (self.user_id)

        qres = self.user_graph.query(query)
        # notification threshold for each change type
        user_email = None
        for row in qres:
            user_email = str(row[0])
        return user_email

    def send_notification_email(self):
        port = 465  # For SSL
        smtp_server = "smtp.gmail.com"
        sender_email = "alexrandles0@gmail.com"  # Enter your address
        receiver_email = self.user_email  # Enter receiver address
        password = "Flowers124!"
        msg = MIMEMultipart()

        msg['From'] = "Alex"
        msg['To'] = receiver_email
        msg['Subject'] = "Notification - Change Detection System"

        body = "Hi, \n\n" \
               "The notification policy conditions have been satisfied. The graph containing the changes, notification policy and contact details is attached."

        msg.attach(MIMEText(body, 'plain'))

        filename = "graph.trig"
        attachment = open("/home/alex/Desktop/Mapping-Quality-Framework/change_detection/database_change_detection/user_files/graphs/user_1.trig", "rb")

        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachment).read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % filename)

        msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()

if __name__ == "__main__":
    ValidateNotificationPolicy("/home/alex/MQI-Framework/static/change_detection_cache/change_graphs/10.trig", "11")