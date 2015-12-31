import logging
import requests
import lxml.html
from requests_kerberos import HTTPKerberosAuth, DISABLED


def mojo_auth():
    jive_ssologin=(
        "https://mojo.redhat.com/login.jspa?ssologin=true&fragment=&referer="
        "%252Fapi%252Fcore%252Fv3%252Fpeople%252Fusername%252Fwshi")
    s = requests.Session()
    kerberos_auth = HTTPKerberosAuth(mutual_authentication=DISABLED)

    ##########################
    # SALMRequest token Page #
    ##########################
    # Open mojo sso login page to get SAMLRequest token
    r = s.get(jive_ssologin)
    # There's hidden SAMLRequest form
    root = lxml.html.document_fromstring(r.text)
    samlrequest = root.xpath('//input[@name="SAMLRequest"]')[0].value
    relaystate = root.xpath('//input[@name="RelayState"]')[0].value
    post_url = root.xpath('//form[@method="post"]')[0].action
    data = {'RelayState': relaystate, 'SAMLRequest': samlrequest}
    # POST https://saml.redhat.com/idp/ use SPNEGO to negotiate with Kerberos
    r = s.post(post_url, data=data, auth=kerberos_auth)
    # On https://saml.redhat.com/idp/ (Red Hat Internal SSO)
    authenticate = r.headers.get("www-authenticate", "")
    r = s.post(post_url, data=data, headers={'Authorization': authenticate})

    ###########################
    # SALMResponse token Page #
    ###########################
    root = lxml.html.document_fromstring(r.text)
    samlresponse = root.xpath('//input[@name="SAMLResponse"]')[0].value
    relaystate = root.xpath('//input[@name="RelayState"]')[0].value
    post_url = root.xpath('//form[@method="POST"]')[0].action
    data = {'SAMLResponse': samlresponse, 'RelayState': relaystate}
    s.post(post_url, data=data)
    cookies = s.cookies.get_dict()
    s.close()

    return cookies

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    cookies = mojo_auth()
    base_url = "https://mojo.redhat.com/api/core/v3/"
    url = 'contents?filter=entityDescriptor(102,1059497)'
    s = requests.Session()
    r = s.get(base_url+url, cookies=cookies)
    print(r.text)
