import requests
import json
import re
import logging
from HTMLParser import HTMLParser
from BeautifulSoup import BeautifulSoup
from datetime import datetime


class MOJOSession(object):
    def __init__(self, username, password):
        user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:34.0) Gecko/20100101 Firefox/34.0"
        base_url = "https://mojo.redhat.com/api/core/v3/"
        # init requests session
        self.base_url = base_url
        self.s = requests.Session()
        self.s.auth = (username, password)
        headers = {"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Encoding":"gzip, deflate",
                    "Accept-Language":"en-US,en;q=0.5",
                    "Cache-Control":"no-cache",
                    "Connection":"keep-alive",
                    "User-Agent": user_agent}
        self.s.headers.update(headers)
        self.r = None

    def get(self, url):
        logging.info("Making api get call to %s" % url)
        try:
            self.r = self.s.get(url, verify=False, headers={'Content-Type':'application/json'})
        except:
            logging.error("connection to mojo failed")
        # convert response to json
        return self.__json()

    def post(self, url, data):
        logging.info("Making api post call to %s" % url)
        try:
            self.r = self.s.post(url, data=data, verify=False, headers={'Content-Type':'application/json'})
        except:
            logging.error("connection to mojo failed")
        # convert response to json
        return self.__json()

    def put(self, url, data):
        logging.info("Making api put call to %s" % url)
        try:
            self.r = self.s.put(url, data=data, verify=False, headers={'Content-Type':'application/json'})
        except:
            logging.error("connection to mojo failed")
        # convert response to json
        return self.__json()

    def delete(self, url):
        logging.info("Making api delete call to %s" % url)
        try:
            self.r = self.s.delete(url, verify=False, headers={'Content-Type':'application/json'})
        except:
            logging.error("connection to mojo failed")
        # convert response to json
        return self.__json()

    def __json(self):
        json_string = re.sub(r"throw.*;\s*","",self.r.text)
        try:
            json_obj = json.loads(json_string)
            return json_obj
        except:
            logging.error("Unable to convert string to json\n %s" % json_string)


class MOJOApi(MOJOSession):
    def __init__(self, username, password):
        super(MOJOApi, self).__init__(username, password)

    def document2content(self, doc_id):
        """ Get content_id from document_id """
        logging.info("Getting content_id from document_id %s" % doc_id)
        url = requests.compat.urljoin(self.base_url, "contents?filter=entityDescriptor(102,%s)" % doc_id)
        j_content = self.get(url)
        if len(j_content['list']) != 1:
            logging.error("document2content return %s contents" % len(j_content['list']))
        url_content = j_content['list'][0]['resources']['self']['ref']
        return url_content

    def create_document(self, subject, text, place_id=None):
        """ Create document """
        logging.info("Creating document")
        j_doc = {"content": {"type": "text/html"}, "type": "document"}
        j_doc["subject"] = subject
        j_doc["content"]["text"] = text
        if place_id:
            j_doc["visibility"] = "place"
            j_doc["parent"] = requests.compat.urljoin(self.base_url, "places/%s" % place_id)
        str_doc = json.dumps(j_doc)
        url = requests.compat.urljoin(self.base_url, "contents")
        j_doc = mojo.post(url, str_doc)
        url_doc = j_doc["resources"]["html"]["ref"]
        return url_doc

    def update_document(self, doc_id, text):
        """ Update document """
        logging.info("Update document %s" % doc_id)
        url_content = self.document2content(doc_id)
        j_doc = self.get(url_content)
        j_doc["content"]["text"] = '<body><div class="jive-rendered-content"><p>' + text + '</p></div></body>'
        str_doc = json.dumps(j_doc)
        mojo.put(url_content, str_doc)
        if self.r.status_code != 200:
            logging.error("Update doc %s error with code %s, text %s" % (doc_id, self.r.status_code, self.r.text))
            return self.r.status_code
        return 0

    def delete_document(self, doc_id):
        """ Delete document """
        logging.info("Delete document %s" % doc_id)
        url_content = self.document2content(doc_id)
        self.delete(url_content)
        if self.r.status_code != 204:
            logging.error("Delete doc %s error with code %s, text %s" % (doc_id, self.r.status_code, self.r.text))
            return self.r.status_code
        return 0

    def get_user(self, username):
        """ Get user info from mojo """
        logging.info("Getting username %s" % username)
        url = requests.compat.urljoin(self.base_url, "people/username/%s" % username)
        return self.get(url)

    def create_task(self, place_id, data):
        """ Create task in mojo place (project)"""
        logging.info("Creating task: %s" % data['subject'])
        url = requests.compat.urljoin(self.base_url, "places/%s/tasks" % place_id)
        return self.post(url, json.dumps(data))

    def create_project(self, parent_place_id, name, display_name, start_date, due_date, **kwargs):
        """ Create project in mojo place (place)"""
        data = dict(
            parent=requests.compat.urljoin(self.base_url, "places/%s" % parent_place_id),
            name=name,
            displayName=display_name,
            startDate=start_date.strftime("%Y-%m-%dT%H:%M:%S%z") if type(start_date) is datetime else start_date, # required in "2012-07-02T07:00:00.000+0000" format
            dueDate=due_date.strftime("%Y-%m-%dT%H:%M:%S%z") if type(due_date) is datetime else due_date, # required in "2012-07-02T07:00:00.000+0000" format
            type="project",
            )
        data.update(kwargs)
        logging.info("Creating project: %s" % data)
        url = requests.compat.urljoin(self.base_url, "places")
        return self.post(url, json.dumps(data))

    def create_checkpoints(self, place_id, data):
        """ Create checkpoints for a mojo project"""
        logging.info("Creating project checkpoints")
        url = requests.compat.urljoin(self.base_url, "checkpoints/%s" % place_id)
        return self.post(url, json.dumps(data))

    def parse_html(self, j_doc):
        """ Parse html content for document """
#       parser = MyHTMLParser()
#       parser.feed(j_doc["content"]["text"])
        soup = BeautifulSoup(j_doc["content"]["text"])
        doc_body = ''
        for i in soup.find('div',{'class':'jive-rendered-content'}).contents:
            doc_body += str(i)
        soup = BeautifulSoup(doc_body)
        f = open("soap.html", 'w')
        doc_body_pre = soup.prettify()
        print doc_body_pre
        f.write(doc_body_pre)
        f.close()


class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.recording = 0
        self.data = []
        self.count = 0

    def handle_starttag(self, tag, attributes):
        if tag != 'div':
            return
        for name, value in attributes:
            if name == 'class' and value == 'jive-rendered-content':
                self.recording = 1
            else:
                self.recording -= 1
                return

    def handle_endtag(self, tag):
        if tag == 'div' and self.recording:
            self.recording -= 1

    def handle_data(self, data):
        if self.recording:
            self.count += 1
            print('wshi---' + str(self.count))
            print(data)
            self.data = data


if __name__ == "__main__":
    import sys
    kerb_username = sys.argv[1]
    kerb_password = sys.argv[2]
    #doc_id = raw_input("Doc id : ")
    #place 251888
    mojo = MOJOApi(kerb_username, kerb_password)
#    x = mojo.delete_document(1009456)
    print mojo.create_document("test", "content")
#    x = mojo.update_document(1009457, "update")
    exit(0)
