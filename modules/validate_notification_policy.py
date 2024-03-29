import rdflib
import smtplib
import os
import time
import dateutil
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime


class ValidateNotificationPolicy:

    def __init__(self, graph_file, user_id):
        print("validating notification policy", graph_file)
        self.user_id = user_id
        self.graph_file = graph_file
        self.user_graph = rdflib.Dataset()
        self.user_graph.parse(graph_file, format="trig")
        self.user_email = self.get_user_email()
        self.detection_period = self.get_detection_period()
        print(self.detection_period)
        self.changes_count = self.get_changes_count()
        self.notification_thresholds = self.get_notification_thresholds()
        self.validate_policy()

    def validate_policy(self):
        total_threshold = sum([int(threshold) for threshold in self.notification_thresholds.values()])
        change_count = sum([int(change) for change in self.changes_count.values()])
        if total_threshold <= change_count:
            message = f"Your notification policy total threshold is {total_threshold} and the framework has detected {change_count} changes."
            self.send_notification_email(message)
        current_date =  datetime.now()
        if current_date < self.detection_period:
            message = f"Your notification policy end date {self.detection_period} has been reached."
            # self.send_notification_email(message)

    def get_detection_period(self):
        # get detection time for notification policy to check if still valid
        query = """
            PREFIX oscd: <https://www.w3id.org/OSCD#>
            PREFIX rei-policy: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiPolicy.owl#>
            SELECT ?detectionStart ?detectionEnd
            WHERE
            {
              GRAPH ?changesGraph  {
                ?policy a rei-policy:Policy ;
                        oscd:hasDetectionEnd ?detectionEnd;
                        oscd:hasDetectionStart ?detectionStart .
              }
            }
        """
        qres = self.user_graph.query(query)
        detection_time = None
        for row in qres:
            detection_time = row.get("detectionEnd")
        # convert detection period into datetime format
        detection_time = dateutil.parser.parse(detection_time)
        return detection_time

    def get_changes_count(self):
        # query to get notification thresholds
        query = """
        PREFIX oscd: <https://www.w3id.org/OSCD#> 
        # GET COUNT FOR EACH CHANGE TYPE
        SELECT ?changeType (count(?change) AS ?count)
        WHERE
        {
          # QUERY USER GRAPH
          GRAPH ?g {
            # GET DIFFERENT CHANGE TYPES
            VALUES ?changeType
            {
                       oscd:InsertSourceData
                       oscd:DeleteSourceData
                       oscd:MoveSourceData
                       oscd:UpdateSourceData
                       oscd:MergeSourceData
                       oscd:DatatypeSourceData
                     }
                    # GET EACH CHANGE FROM LOG
                     ?changeLog a oscd:ChangeLog ;
                                oscd:hasChange ?change.
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
        PREFIX rei-constraint: <http://www.cs.umbc.edu/~lkagal1/rei/ontologies/ReiConstraint.owl#>
 
        SELECT ?changeType ?threshold
        WHERE
        {
          # QUERY NOTIFICATION GRAPH
          GRAPH ?g  {
            # GET THRESHOLD FOR EACH CHANGE TYPE
            ?constraint a rei-constraint:SimpleConstraint;
               rei-constraint:subject ?changeType;
               rei-constraint:object ?threshold .
          }
        }
        """
        qres = self.user_graph.query(query)
        # notification threshold for each change type
        notification_thresholds = {}
        for row in qres:
            notification_thresholds[row[0]] = row[1]
        return notification_thresholds

    def get_user_email(self):
        # query to find thresholds within notification policy
        query = """
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            SELECT ?email
            WHERE
            {
              GRAPH ?g {
                ?user a foaf:Agent;
                      foaf:mbox ?email .
              }
            }
        """
        qres = self.user_graph.query(query)
        # notification threshold for each change type
        user_email = None
        for row in qres:
            user_email = str(row.get("email"))
        return user_email

    def send_notification_email(self, message):
        msg = MIMEMultipart()
        sender = "alex.randles@outlook.com"
        recipient = self.user_email

        msg['Subject'] = "Notification for Change Detection System"
        msg['From'] = sender
        msg['To'] = recipient

        body = f"Hi, \n\nThe notification policy has been satisfied.\n\nThe graph containing the changes, notification policy and contact details is attached.\n{message}"

        msg.attach(MIMEText(body, 'plain'))

        attachment = open(self.graph_file, "rb")

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        email.encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename= %s" % "change_graph.trig")

        msg.attach(part)
        email_message = email.message.EmailMessage()
        email_message.set_content(msg)

        try:
            smtp = smtplib.SMTP("smtp-mail.outlook.com", port=587)
            smtp.starttls()
            smtp.login(sender, "R7LwqD9rMnERh9Q")
            smtp.sendmail(sender, recipient, email_message.as_string())
            smtp.quit()
        except smtplib.SMTPAuthenticationError as e:
            print("Sending email exception", e)


if __name__ == "__main__":
    ValidateNotificationPolicy("/home/alex/MQI-Framework/static/change_detection_cache/change_graphs/3.trig", "11")
