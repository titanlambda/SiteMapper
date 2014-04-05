from IronWASP import *
import re


#Extend the Module base class
class SiteMapper(Module):


  #Implement the GetInstance method of Module class. This method is used to create new instances of this module.
  def GetInstance(self):
    m = SiteMapper()
    m.Name = 'SiteMapper'
    return m


  #Implement the StartModule method of Module class. This is the method called by IronWASP when user tries to launch the moduule from the UI.
  def StartModule(self):
    #IronConsole is a CLI window where output can be printed and user input accepted
    self.console = IronConsole()
    self.console.SetTitle('SiteMapper - Mapping of website based on their reference in the response')
    #Add an event handler to the close event of the console so that the module can be terminated when the user closes the console
    self.console.ConsoleClosing += lambda e: self.close_console(e)
    self.console.ShowConsole()
    #'PrintLine' prints text at the CLI. 'Print' prints text without adding a newline at the end.
    self.console.PrintLine('[*] SiteMapper - Mapping of website based on their reference in the response has started')
    self.console.Print('Do you want to start analysis? Y/N ')
    #'ReadLine' accepts a single line input from the user through the CLI. 'Read' accepts multi-line input.
    ans = self.console.ReadLine()
    if(ans == "Y" or ans == 'y'):
      self.StartMapping()



  def close_console(self, e):
    #This method terminates the main thread on which the module is running
    self.StopModule()


  
  #remove http, https, www, / at end, strip leading or trailing white spaces

  def StripHTTPStrings(self, href):
    http="http://"
    https="https://"
    www="www."
    if(href.find(http) >= 0):
      href = href[href.find(http) + len(http):]
    if(href.find(https) >= 0):
      href = href[href.find(https) + len(https):]
    if(href.find(www) >= 0):
      href = href[href.find(www) + len(www):]
    return href

  def FilterDuplicateURLs(self, hrefs, excludeURLList=[]):
    seen = set();
    result = [];
    for href in hrefs:
      if(self.UrlNotInExcludeList(href, excludeURLList)):
        req = Request(href)
        if (req != None and req.BaseUrl != None):
          url=self.StripHTTPStrings(href)
          url = url.strip()
          url = url.strip("/")
          if len(url) > 2 and url not in seen:
            seen.add(url);
            result.append(url);
    return result;

  def UrlNotInExcludeList(self, href, excludeURLList):
    for badURL in excludeURLList:
      if(badURL in href):
        return False
    return True
    
  def FindURLsUsingRegEx(self, responseBodyString):
    _REGEX_VALID_URL_SIMPLE = re.compile(
          'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    return _REGEX_VALID_URL_SIMPLE.findall(responseBodyString)


  def CreateJsonText(self, jsonList):
    textOutput = "{ \"name\":\"LOGS\", \"children\":["
    for row in jsonList:
      textOutput = textOutput + self.CreateJsonTextForEachDomain(row) + ","
    textOutput = textOutput.strip(",")
    textOutput = textOutput + "]}"
    return textOutput

  def CreateJsonTextForEachDomain(self, row):
    textOutput = "{"
    elements = row.split("=>")
    root = elements[0].strip()
    textOutput = textOutput + "\"name\":\"" + root + "\", \"children\":[" 
    children = elements[1]
    childrenList = children.split(",")
    for child in childrenList:
      childText = "{ \"name\": \"" +  child.strip() + "\" },"
      textOutput = textOutput + childText
    textOutput = textOutput.strip(",")
    textOutput = textOutput + "]}"
    return textOutput	


  def StartMapping(self):
    temp_list=[]
    self.console.PrintLine(" ")
    self.console.PrintLine("\n\n\n ######## STARTING MAPPING ########")

    for i in range(Config.LastProxyLogId):
      sess = Session.FromProxyLog(i+1)
      temp_list.append(sess.Request.BaseUrl)
      if (sess.Response != None and sess.Response.HasBody):

    #GET URLS FROM HREFS
        cs = CookieStore()
        link_requests = Crawler.GetLinkClicks(sess.Request, sess.Response, cs)
        for link_req in link_requests:
          temp_list.append(link_req.BaseUrl.split("?")[0].split("\\")[0])


    #GET URLS USING REGEX MATCH
        urlListFromRegEx = self.FindURLsUsingRegEx(sess.Response.BodyString)
        for url in urlListFromRegEx:
          req = Request(url)
          if (req != None):
            temp_list.append(req.BaseUrl.split("?")[0].split("\\")[0])

    filtered_list = self.FilterDuplicateURLs(temp_list)

    self.console.PrintLine( "\n########### NUMBER OF URL FOUND -> " )
    self.console.PrintLine( len(filtered_list))


    url_dict = {}

    for url in filtered_list:
      url_dict[url]=""

    #We find out the number of logs in the selected log source and loop through it
    for i in range(Config.LastProxyLogId):
      sess = Session.FromProxyLog(i+1)
      if(sess.Response != None and sess.Response.HasBody):
        key =""
        for url in filtered_list:
          baseURL = self.StripHTTPStrings(sess.Request.BaseUrl)
          baseURL = baseURL.strip()
          baseURL = baseURL.strip("/")
          if url == baseURL:
            key = url
      
        for url in filtered_list:
          if url not in key and url in sess.Response.BodyString and url not in url_dict[key]:
            url_dict[key]= url_dict[key] + ',' + url


    jsonList = []

    for k, v in url_dict.items():
    # Display key and value.
      if v:
        record = k + " => " + v.strip(",")
        jsonList.append(record)


    self.console.PrintLine( "\n\n ######## MAPPING DONE... TEXT MAPPING -> \n")
    self.console.PrintLine( jsonList)


    jsonText = self.CreateJsonText(jsonList)


    # CREATING LINEAR MAPPING
    f_html = open(Config.Path + '\\modules\\SiteMapper\\Mapping_Linear.html','w')
    with open(Config.Path + '\\modules\\SiteMapper\\d3\\d3_Linear_Begin_template.html','r') as f:
      mapping_Linear_Begin_template = f.readlines();
    f.close();
    for line in mapping_Linear_Begin_template:
      f_html.write(line)
    jsonVar = "\n\t\tvar myJSON = \"" + jsonText.replace('"', '\\"') + "\";\n"
    f_html.write(jsonVar)
    with open(Config.Path + '\\modules\\SiteMapper\\d3\\d3_Linear_End_template.html','r') as f:
      mapping_Linear_End_template = f.readlines();
    f.close();
    for line in mapping_Linear_End_template:
      f_html.write(line)
    f_html.close()

    # CREATING CIRCULAR MAPPING
    f_html = open(Config.Path + '\\modules\\SiteMapper\\Mapping_Circular.html','w')
    with open(Config.Path + '\\modules\\SiteMapper\\d3\\d3_Circular_Begin_template.html','r') as f:
      mapping_Circular_Begin_template = f.readlines();
    f.close();
    for line in mapping_Circular_Begin_template:
      f_html.write(line)
    jsonVar = "\n\t\tvar myJSON = \"" + jsonText.replace('"', '\\"') + "\";\n"
    f_html.write(jsonVar)
    with open(Config.Path + '\\modules\\SiteMapper\\d3\\d3_Circular_End_template.html','r') as f:
      mapping_Circular_End_template = f.readlines();
    f.close();
    for line in mapping_Circular_End_template:
      f_html.write(line)
    f_html.close()
	
    self.console.PrintLine(" ")
    self.console.PrintLine("###################################################################################################")
    self.console.PrintLine("######## MAPPING DONE... SAVED IN FILE! ########")
    self.console.PrintLine("###################################################################################################")
    self.console.PrintLine("The liner mapping graph is saved as " + Config.Path + "\\modules\\SiteMapper\\Mapping_Linear.html.html")
    self.console.PrintLine(" ")
    self.console.PrintLine("The circular mapping graph is saved as " + Config.Path + "\\modules\\SiteMapper\\Mapping_Circular.html")
    self.console.PrintLine("###################################################################################################")

#This code is executed only once when this new module is loaded in to the memory.
#Create an instance of the this module
m = SiteMapper()
#Call the GetInstance method on this instance which will return a new instance with all the approriate values filled in. Add this new instance to the list of Modules
Module.Add(m.GetInstance())
