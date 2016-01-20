import requests
# Disable HTTPS verification warnings.
try:
    from requests.packages import urllib3
except ImportError:
    pass
else:
    urllib3.disable_warnings()
import urllib
import json
import re
import logging
import mailbox
from HTMLParser import HTMLParser
from bs4 import BeautifulSoup
import bs4
import datetime
import gzip
import os
from mojo_auth import mojo_auth


class MOJOSession(object):
    def __init__(self):
        self.s = requests.Session()
        headers = {'Content-Type': 'application/json'}
        self.s.headers.update(headers)
        self.cookies = mojo_auth()
        self.r = None

    def get(self, url):
        logging.debug("Making api get call to %s" % url)
        try:
            self.r = self.s.get(url, cookies=self.cookies)
        except:
            logging.error("connection to mojo failed")
        # convert response to json
        return self.__json()

    def post(self, url, data):
        logging.debug("Making api post call to %s" % url)
        try:
            self.r = self.s.post(url, data=data, cookies=self.cookies)
        except:
            logging.error("connection to mojo failed")
        # convert response to json
        return self.__json()

    def put(self, url, data):
        logging.debug("Making api put call to %s" % url)
        try:
            self.r = self.s.put(url, data=data, cookies=self.cookies)
        except:
            logging.error("connection to mojo failed")
        # convert response to json
        return self.__json()

    def delete(self, url):
        logging.debug("Making api delete call to %s" % url)
        try:
            self.r = self.s.delete(url, cookies=self.cookies)
        except:
            logging.error("connection to mojo failed")

    def __json(self):
        json_string = re.sub(r"throw.*;\s*", "", self.r.text)
        try:
            json_obj = json.loads(json_string)
            return json_obj
        except:
            logging.error("Unable to convert string to json\n %s" % json_string)


class MOJOApi(MOJOSession):
    def __init__(self):
        super(MOJOApi, self).__init__()
        base_url = "https://mojo.redhat.com/api/core/v3/"
        self.base_url = base_url

    def document2content(self, doc_id):
        """ Get content_id from document_id """
        logging.info("Getting content_id from document_id %s" % doc_id)
        url = requests.compat.urljoin(self.base_url, "contents?filter=entityDescriptor(102,%s)" % doc_id)
        j_content = self.get(url)
        if self.r.status_code == 404:
            logging.error("Document %s not found." % doc_id)
            exit(self.r.status_code)
        if len(j_content['list']) != 1:
            logging.error("document2content return %s contents" % len(j_content['list']))
        url_content = j_content['list'][0]['resources']['self']['ref']
        return url_content

    def create_document(self, subject, text, place_id=None):
        """ Create document """
        logging.info("Creating document")
        j_doc = dict(content={"type": "text/html"}, type="document")
        j_doc["subject"] = subject
        j_doc["content"]["text"] = text
        if place_id:
            j_doc["visibility"] = "place"
            j_doc["parent"] = requests.compat.urljoin(self.base_url, "places/%s" % place_id)
        str_doc = json.dumps(j_doc)
        url = requests.compat.urljoin(self.base_url, "contents")
        j_doc = self.post(url, str_doc)
        url_doc = j_doc["resources"]["html"]["ref"]
        return url_doc

    def update_document(self, doc_id, text):
        """ Update document """
        logging.info("Update document %s" % doc_id)
        url_content = self.document2content(doc_id)
        j_doc = self.get(url_content)
        j_doc["content"]["text"] = '<body><div class="jive-rendered-content"><p>' + text + '</p></div></body>'
        str_doc = json.dumps(j_doc)
        self.put(url_content, str_doc)
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

    def get_document(self, doc_id):
        """ Get document """
        logging.info("Get document %s" % doc_id)
        url_content = self.document2content(doc_id)
        doc = self.get(url_content)
        html = self.get_html(doc, prettify=False)
        if self.r.status_code != 200:
            logging.error("GET doc %s error with code %s, text %s" % (doc_id, self.r.status_code, self.r.text))
            return self.r.status_code
        return html

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

    @staticmethod
    def get_html(j_doc, prettify=True):
        """ Parse html content for document """
        # parser = MyHTMLParser()
        # parser.feed(j_doc["content"]["text"])
        soup = BeautifulSoup(j_doc["content"]["text"])
        doc_body = ''
        for i in soup.find('div', {'class': 'jive-rendered-content'}).contents:
            doc_body += str(i)
        if not prettify:
            return doc_body
        soup = BeautifulSoup(doc_body)
        f = open("soap.html", 'w')
        doc_body = soup.prettify()
        f.write(doc_body.encode("UTF-8"))
        f.close()
        return doc_body

    @staticmethod
    def text2html(text):
        """ Generate html """
        html_src = '<body>'
        for l in text.splitlines():
            if re.match('^\s*$', l):
                html_src += '<p></p>\n'
            else:
                l = l.replace('&', '&amp;')
                l = l.replace('<', '&lt;')
                l = l.replace('>', '&gt;')
                html_src = html_src + '<p>'+l+'</p>\n'
        html_src += '</body>'
        # for debugging
        # f = open('test.html', 'w')
        # f.write(html_src)
        # f.close()

        return html_src


class EmailHelper(object):
    def __init__(self, mail_list=None, tmp_dir='/tmp/', filter_method='default', filter_key=None):
        self.tmp_dir = tmp_dir
        if not mail_list:
            self.email_archives = 'http://post-office.corp.redhat.com/archives/virt-qe-list/'
        else:
            self.email_archives = 'http://post-office.corp.redhat.com/archives/' + mail_list + '/'
            r = urllib.urlopen(self.email_archives)
            if r.code != 200:
                logging.error('Invalid mail list given: %s, HTTP request got error code: %s' % (mail_list, r.code))
                exit(r.code)
        self.filter_method = filter_method
        if filter_key:
            self.filter_key = filter_key
        else:
            self.filter_key = ''

    def download_mbox(self, name):
        download_url = self.email_archives + name + '.txt.gz'
        local_path_zipped = self.tmp_dir + name + '.txt.gz'
        local_path = self.tmp_dir + name + '.txt'
        urllib.urlretrieve(download_url, local_path_zipped)
        in_f = gzip.GzipFile(local_path_zipped, 'rb')
        s = in_f.read()
        in_f.close()
        out_f = file(local_path, 'wb')
        out_f.write(s)
        out_f.close()

    def load_mbox(self, name):
        file_name = self.tmp_dir + name + '.txt'
        mbox = mailbox.mbox(file_name)
        for message in mbox:
            # print re.sub('\n\s+', ' ', message['subject'])
            if self.filter(message):
                yield {"subject": re.sub('\n\s+', ' ', message['subject']), "body": self.get_body(message)}
        mbox.close()

    def clean_mbox(self, name):
        os.remove(self.tmp_dir + name + '.txt')
        os.remove(self.tmp_dir + name + '.txt.gz')

    @staticmethod
    def get_body(msg):
        body = None
        # Walk through the parts of the email to find the text body.
        if msg.is_multipart():
            for part in msg.walk():
                # If part is multipart, walk through the subparts.
                if part.is_multipart():
                    for subpart in part.walk():
                        if subpart.get_content_type() == 'text/plain':
                            # Get the subpart payload (i.e the message body)
                            body = subpart.get_payload(decode=True)
                            # charset = subpart.get_charset()
                # Part isn't multipart so get the email body
                elif part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True)
                    # charset = part.get_charset()
        # If this isn't a multi-part message then get the payload (i.e the message body)
        elif msg.get_content_type() == 'text/plain':
            body = msg.get_payload(decode=True)
        # special handling for Thunderbird which use markup syntax in text/plain
        for header in msg._headers:
            if header[0] == 'User-Agent' and 'Thunderbird' in header[1]:
                tmp = body.replace('*', ' ')
                body = re.sub('<[^>]*>', '', tmp)
        return body

    def filter_body(self, msg):
        body = self.get_body(msg)
        if type(body) is not str:
            return False
        if self.filter_key in body:
            return True
        else:
            return False

    def filter_subject(self, msg):
        if self.filter_key == '':
            self.filter_key = '^RHEV-H 7.0 for RHEV 3.5*'
        if re.match(self.filter_key, msg['subject'], re.DOTALL):
            return True
        else:
            return False

    def filter_from(self, msg):
        if self.filter_key in msg._from:
            return True
        else:
            return False

    def filter(self, msg):
        if self.filter_method == 'subject':
            return self.filter_subject(msg)
        elif self.filter_method == 'from':
            return self.filter_from(msg)
        elif self.filter_method == 'body':
            return self.filter_body(msg)
        else:
            return self.filter_subject(msg)


class Report(object):
    """
    report={'month': 'yyyy-mm', 'ref': 'email'}
    email={'subject': 'xxxx', 'body': 'xxxx', 'ref': 'mojo_link'}
    """
    def __init__(self, mojo, months=None, skip=0, place_id=None, doc_id=None, title='MOJO Report', mail_list=None, filter_method='subject', filter_key=None):
        self.mojo = mojo
        self.email = EmailHelper(mail_list=mail_list, filter_method=filter_method, filter_key=filter_key)
        self.months_update = []
        self.months_list = {}
        self.title = title
        if not months:
            months = 3
        if place_id:
            try:
                test_place_id = int(place_id)
                logging.info("Place ID = %d" % test_place_id)
                self.place_id = test_place_id
            except ValueError:
                self.place_id = None
                logging.error("Place ID is string: %s" % place_id)
        else:
            self.place_id = None
        # for existing report, load it first and update the specify months
        # for new report, create a new mojo page and load specify months
        if doc_id:
            self.load_report()
        date = datetime.datetime.now()
        if skip > 0:
            for i in range(skip):
                date = datetime.date(day=1, month=date.month, year=date.year) - datetime.timedelta(days=1)
        for d in range(months):
            year = date.year
            month = date.strftime("%m")
            logging.debug("Month will be processed: %s" % str(year) + str(month))
            self.months_update.append(str(year) + str(month))
            date = datetime.date(day=1, month=date.month, year=date.year) - datetime.timedelta(days=1)

    @staticmethod
    def gen_report(test_list, catalog):
        html_src = '<p><span style="color: #ff0000;"><strong>'+catalog+'</strong></span></p>\n'
        for i in test_list:
            html_src = html_src + '<p><a href="' + i['ref'] + '">' + i['subject'] + '</a></p>\n'
        html_src += '<p>&nbsp;</p>\n'
        return html_src

    def publish_report(self, doc_id=None, dry_run=False):
        html_src = ''
        for month in self.months_update:
            if month in self.months_list:
                report_items = self.months_list[month]
            else:
                report_items = []
                self.months_list[month] = report_items
            date = datetime.datetime.strptime(month, '%Y%m')
            month = date.strftime('%Y-%B')
            self.email.download_mbox(month)
            emails = self.email.load_mbox(month)
            for i in emails:
                new = False
                if not any(d['subject'] == i['subject'] for d in report_items):
                    new = True
                if new and not dry_run:
                    mojo_link = self.mojo.create_document(i['subject'], self.mojo.text2html(i['body']).replace('\n', ''), place_id=self.place_id)
                    i['ref'] = mojo_link
                    report_items.append(i)
                    logging.info(i['subject'])
                    logging.info(i['ref'])
                elif new and dry_run:
                    i['ref'] = 'dry_run'
                    report_items.append(i)
                    logging.info(i['subject'])
                    logging.info(i['ref'])
            self.email.clean_mbox(month)
            html_src += self.gen_report(report_items, month)
        if dry_run:
            logging.info(html_src)
            return

        if doc_id:
            self.mojo.update_document(doc_id, html_src)
        else:
            mojo_link = self.mojo.create_document(self.title, html_src, place_id=self.place_id)
            logging.info('Here is the mojo link for final report: %s' % self.title)
            logging.info(mojo_link)

    def load_report(self, doc_id):
        html = self.mojo.get_document(doc_id)
        soup = BeautifulSoup(html)
        report_items = []
        old_month = '000000'
        for i in soup.find_all('p'):
            if type(i.next) is not bs4.element.Tag:
                continue
            if i.next.name == 'span' and 'style' in i.next.attrs:
                date = datetime.datetime.strptime(i.text, '%Y-%B')
                cur_month = date.strftime('%Y%m')
                if cur_month != old_month and old_month != '000000':
                    self.months_list[old_month] = report_items
                    report_items = []
                old_month = cur_month
            if i.next.name == 'a' and 'href' in i.next.attrs:
                item = {'subject': i.text.encode("ascii"), 'ref': i.next.attrs['href']}
                report_items.append(item)
        if old_month != '000000':
            self.months_list[old_month] = report_items

    def delete_report(self, doc_id=None):
        if doc_id is None:
            return 1
        url_content = self.mojo.document2content(doc_id)
        j_doc = self.mojo.get(url_content)
        html = self.mojo.get_html(j_doc)
        soup = BeautifulSoup(html, "lxml")
        for a in soup.findAll('a'):
            url = a['href']
            logging.info(url)
            id = re.sub(r'https://mojo.redhat.com/docs/DOC-', "", url)
            self.mojo.delete_document(id)


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
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    import sys
    mojo = MOJOApi()

    report = Report(mojo, mail_list='virt-qe-list', filter_method='body', filter_key='7.2+Virt+QE+-+Week+')
    # report.load_report(1015195)
    # report.publish_report(1015195, dry_run=True)
    # report.publish_report()
    report.delete_report(1060753)
    # sys.exit(0)

    x = mojo.delete_document(1060753)
    # print mojo.create_document("test", "content")
    # x = mojo.update_document(1060649, "update")
    # f = open("data.html", 'r')
    # c = f.read()
    # x = mojo.update_document(1060649, c.replace('\n', ''))
