#!/usr/bin/lua

 

--[[

 

Copyright (c) 2014  Pavel Tisnovsky, Red Hat

 

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the Red Hat nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL Pavel Tisnovsky BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

 

--]]

 

 

 

--
-- This script could be used to update selected document in Jive/Mojo by the
-- content of given HTML input file. Some publican-related styles are supported
-- too by a minor hacking, but this tool should be used for other types of
-- documents too.
--
-- Author: Pavel Tisnovsky <ptisnovs@redhat.com>
--

 


--
-- Module used to read and parse JSON files
--
local json = require("dkjson")

 

 

 

--
-- Mojo URL, username and password should be stored in this configuration file
-- This file should contain three configuration parameters in a form:
--
url="https://mojo.xyzzy.org/api/core/v3/"
username="tester"
password="well_i_cant_recall_it"
--
--dofile("mojo.cfg")

 

 

 

--
-- Read input file and return its content as a string.
--
function readInputFile(inputFileName)

 

    -- info for user (stdout)
    print("    Reading input file: " .. inputFileName)

 

    local fin = io.open(inputFileName, "r")
    local str = fin:read("*all")

 

    -- current position in file = file size at this point
    local current = fin:seek()
    fin:close()

 

    -- info for user (stdout)
    print("    Done. " .. current .. " bytes read.")
    return str
end

 

 

 

--
-- Read input file and convert data from JSON format to a regular Lua object.
--
function readInputFileInJsonFormat(inputFileName)
    -- file contents in a form of string
    local str = readInputFile(inputFileName)
    -- try to parse it as JSON
    return json.decode(str, 1, nil)
end

 

 

 

--
-- Test if some string starts with given substring.
--
function startsWith(String, StartSubstring)
    return string.sub(String, 1, string.len(StartSubstring)) == StartSubstring
end

 

 

 

--
-- Get the prefix for command that calls curl tool to retrieve/push contents.
--
function getCurlCLIPrefix(url, username, password)
    local contentURL = url .. "contents/"
    return "curl -u \"" .. username .. ":" .. password .. "\" -k \"" .. contentURL
end

 

 

 

--
-- Get the prefix for command that calls curl tool to retrieve/push images.
--
function getCurlCLIPrefixImages(url, username, password, fileName)
    local contentURL = url .. "images/"
    return "curl -u \"" .. username .. ":" .. password .. "\" -k -F filedata=@" .. fileName .. " \"" .. contentURL .. "\" > image.json"
end

 

 

 

--
-- Get the full command to fetch document using curl tool.
--
function getFetchDocumentCurlCLI(url, username, password, documentID)
    return getCurlCLIPrefix(url, username, password) .. "?filter=entityDescriptor(102," .. documentID .. ")\" | tail -n+2 > metadata.json"
end

 

 

 

--
-- Get the full command to fetch content of document using curl tool.
--
function getFetchContentCurlCLI(url, username, password, contentID)
    return getCurlCLIPrefix(url, username, password) .. contentID .. "\" > document_in.json"
end

 

 

 

--
-- Format input HTML file by using xmllint tool.
-- We need to set the variable XMLLINT_INDENT to empty string because Jive/Mojo
-- does not like indented HTML (it inserts empty <p>...</p> as a replacement for spaces)
--
function formatHTML(originalFileName, formattedFileName)
    os.execute("export XMLLINT_INDENT='';xmllint --format " .. originalFileName .. " > " .. formattedFileName)
end

 

 

 

--
-- Update given anchor - it must consist of lowercase characters and should
-- contain only dash as a separator.
--
function updateAnchor(anchor)
    local str = anchor:lower()
    str = str:gsub("_", "-")
    return str
end

 

 

 

--
-- Write new line to an intermediate file. "\n" characters are inserted too,
-- because we need to take care of all <pre></pre> and <code></code> sections.
-- (yes...Jive/Mojo joins all lines at the time of importing new document
--
function writeLine(fout, line)
    local str = line:gsub("\"", "\\\"")
    fout:write(str .. "\\n\n")
end

 

hrefStart = "<a href=\"#"
hrefStart2 = "<a class=\"xref\" href=\"#"
anchorStart = "<a id=\""

 

 

 

--
-- Push image into Mojo and return its URL.
--
function pushImage(url, username, password, imageName)
    local curlCLI = getCurlCLIPrefixImages(url, username, password, imageName)
    print("    calling: " .. curlCLI)
    os.execute(curlCLI)
    local data = readInputFileInJsonFormat("image.json")
    return data["ref"]
end

 

 

 

--
-- Update all Xrefs in HTML file and do other minor stuff on the given file
-- to conform with some specialities on Jive/Mojo.
--
function updateXrefs(inputFileName, outputFileName, documentID, url, username, password)
    local documentHref = "https://mojo.redhat.com/docs/DOC-" .. documentID
    local fin = io.open(inputFileName, "r")
    local fout = io.open(outputFileName, "w")

 

    -- don't do anything with <head></head> section
    -- (we need to import only <body></body> section)
    while true do
      -- read one line
      local line = fin:read("*l")

 

      -- check for end of file
      if line == nil then
          break
      end

 

      -- check for end of <head> section
      if startsWith(line, "<body") then
          break
      end
    end

 

    -- now let's process the whole <body> section
    while true do
      -- read one line
      local line = fin:read("*l")

 

      -- check for end of file
      if line == nil then
          break
      end

 

      -- now the madness starts
      if line:find(hrefStart) then
          local hrefStartIndex = line:find(hrefStart) + string.len(hrefStart) - 1
          local hrefEndIndex = line:find("\">", hrefStartIndex - 1)
          local localLink = line:sub(hrefStartIndex + 1, hrefEndIndex - 1)
          local newLocalLink = updateAnchor(localLink)
          -- do we really neeed to use the full path to document?
          local newLine = line:sub(1, hrefStartIndex -1) .. documentHref .. "#" .. newLocalLink .. line:sub(hrefEndIndex)
          --local newLine = line:sub(1, hrefStartIndex -1) .. "#" .. newLocalLink .. line:sub(hrefEndIndex)
          writeLine(fout, newLine)
      elseif line:find(hrefStart2) then
          local hrefStart2Index = line:find(hrefStart2) + string.len(hrefStart2) - 1
          local hrefEndIndex = line:find("\">", hrefStart2Index - 1)
          local localLink = line:sub(hrefStart2Index + 1, hrefEndIndex - 1)
          local newLocalLink = updateAnchor(localLink)
          local newLine = line:sub(1, hrefStart2Index -1) .. documentHref .. "#" .. newLocalLink .. line:sub(hrefEndIndex)
          --local newLine = line:sub(1, hrefStart2Index -1) .. "#" .. newLocalLink .. line:sub(hrefEndIndex)
          writeLine(fout, newLine)
      elseif line:find(anchorStart) then
          local newLine = "***"
          local anchorStartIndex = line:find(anchorStart) + string.len(anchorStart) - 1
          local anchorEndIndex = line:find("\">", anchorStartIndex - 1)
          local anchor = line:sub(anchorStartIndex + 1, anchorEndIndex - 1)
          local newAnchor = updateAnchor(anchor)
          local newLine = line:sub(1, anchorStartIndex - 4) .. "name=\"" .. newAnchor .. line:sub(anchorEndIndex)
          writeLine(fout, newLine)
      elseif line:find("class=\"remark\"") then
          local newLine = line:gsub("class=\"remark\"", "style='background-color:#ffff00'")
          writeLine(fout, newLine)
      elseif line:find("<pre class=\"screen\">") then
          local newLine = line:gsub("<pre class=\"screen\">", "<pre class=\"screen\" style='white-space:pre-wrap;background-color:#d0d0d0'>")
          writeLine(fout, newLine)
      elseif line:find("<pre class=\"programlisting\">") then
          local newLine = line:gsub("<pre class=\"programlisting\">", "<pre class=\"programlisting\" style='white-space:pre-wrap;background-color:#d0d0d0'>")
          writeLine(fout, newLine)
      elseif line:find("<span class=\"firstname\">") then
          local newLine = line:gsub("<span class=\"firstname\">", "<span class=\"firstname\" style='margin:5px'>")
          writeLine(fout, newLine)
      elseif line:find("<span class=\"surname\">") then
          local newLine = line:gsub("<span class=\"surname\">", "<span class=\"surname\" style='margin:5px'>")
          writeLine(fout, newLine)
      elseif line:find("class=\"productname\"") then
          local newLine = line:gsub("class=\"productname\"", "class=\"productname\" style='margin:5px'")
          writeLine(fout, newLine)
      elseif line:find("class=\"productnumber\"") then
          local newLine = line:gsub("class=\"productnumber\"", "class=\"productnumber\" style='margin:5px'")
          writeLine(fout, newLine)
      elseif line:find("class=\"orgname\"") then
          local newLine = line:gsub("class=\"orgname\"", "class=\"orgname\" style='margin:5px'")
          writeLine(fout, newLine)
      elseif line:find("class=\"orgdiv\"") then
          local newLine = line:gsub("class=\"orgdiv\"", "class=\"orgdiv\" style='margin:5px'")
          writeLine(fout, newLine)
      elseif line:find("<img .*src=\"") then
          local startIndex, endIndex = line:find("src=\".*.png\"")
          local imageName = line:sub(startIndex+5, endIndex-1)
          local pushedImageURL = pushImage(url, username, password, imageName)
          print(imageName)
          print(pushedImageURL)
          local newLine = line:gsub("src=\".*.png\"", "src=\""..pushedImageURL .."\"")
          writeLine(fout, newLine)
      elseif line=="<dl>" or line =="<dl class=\"toc\">" then
          writeLine(fout, "<ul style='list-style-type:none'>")
      elseif line=="</dl>" then
          writeLine(fout, "</ul>")
      elseif line=="<dt>" or line=="<dd>" then
          writeLine(fout, "<li>")
      elseif line=="</dt>" or line=="</dd>" then
          writeLine(fout, "</li>")
      elseif line=="</body>" or line=="</html>" or line=="</object>" or startsWith(line, "<object ") then
          -- nothing!
      else
          writeLine(fout, line)
      end
    end

 

    -- current position in file = file size at this point
    local finLength = fin:seek()
    fin:close()

 

    -- current position in file = file size at this point
    local foutLength = fout:seek()
    fout:close();

 

    -- info for user
    print("    " .. finLength .. " bytes read")

 

    -- info for user
    print("    " .. foutLength .. " bytes written")
end

 

 

 

--
-- Print simple help when no parameters are given on command line.
--
function printUsage()
    print("Usage:")
    print("    lua publican2mojo.lua input_html_file mojo_document_number url_prefix")
    print("")
    print("Example:")
    print("    lua publican2mojo.lua errata_lore.html 951053 http://foo.bar.com/")
end

 

 

 

--
-- Get the full command to push content of document using curl tool.
--
function getPushContentCurlCLI(url, username, password, contentID)
    local contentURL = url .. "contents/"
    return "curl -u \"" .. username .. ":" .. password ..
          "\" -X PUT -k --header \"Content-Type: application/json\" -d @document_out.json \"" ..
          contentURL .. contentID .. "\" > /dev/null"
end

 

 

 

--
-- Get document metadata and fetch content ID from it.
--
function fetchContentID(url, username, password, documentID)
    local curlCLI = getFetchDocumentCurlCLI(url, username, password, documentID)
    print("    calling: " .. curlCLI)
    os.execute(curlCLI)

 

    -- read json
    local data = readInputFileInJsonFormat("metadata.json")

 

    local id = nil
    id = data["list"][1]["contentID"]
    if id ~= nil then
        print("    found content ID: " .. id)
        return id
    end
    print("Warning! please check content of the file metadata.json")
    -- something is wrong! (but Mojo's format changes randomly
    for line in io.lines("metadata.json") do
        if startsWith(line, "    \"contentID\" : ") then
            id = string.match(line, "[0-9]+")
            print("    found content ID: " .. id)
        end
    end
    return id
end

 

 

 

--
-- Fetch original document from Mojo.
--
function fetchOriginalDocument(url, username, password, contentID)
    local curlCLI = getFetchContentCurlCLI(url, username, password, contentID)
    print("    calling: " .. curlCLI)
    os.execute(curlCLI)
end

 

 

 

--
-- Push new document into Mojo.
--
function pushNewDocument(url, username, password, contentID)
    local curlCLI = getPushContentCurlCLI(url, username, password, contentID)
    print("    calling: " .. curlCLI)
    os.execute(curlCLI)
end

 

 

 

--
-- Prepare JSON file that need to be send into Mojo.
--
function prepareJSONFile(inputHTMLFileName)
    local fout = io.open("document_out.json", "w")

 

    for line in io.lines("document_in.json") do
        if startsWith(line, "    \"text\" : \"<body>") then
            -- replate this node by the new content
            fout:write("    \"text\" : \"\n")
            for htmlLine in io.lines(inputHTMLFileName) do
                fout:write(htmlLine .. "\n")
            end
            fout:write("    \",\n")
        elseif line == "throw 'allowIllegalResourceCall is false.';" then
            -- nothing, this is usually the first line exported from MOJO,
            -- not part of JSON at all
        else
            fout:write(line .. "\n")
        end
    end

 

    -- current position in file = file size at this point
    local foutLength = fout:seek()
    fout:close();

 

    -- info for user
    print("    " .. foutLength .. " bytes written")
end

 

 

 

--
-- Rule the world!
--
function process(arg)
    local inputFileName = arg[1]
    local documentID = arg[2]

 

    -- check CLI parameters
    if inputFileName == nil or documentID == nil then
        printUsage()
        os.exit(1)
    end

 

    local formattedFileName = "formatted_" .. inputFileName
    local outputFileName = "DOC-" .. documentID .. ".html"

 

    print("Processing input file '" .. inputFileName .. "'")
    formatHTML(inputFileName, formattedFileName)
    updateXrefs(formattedFileName, outputFileName, documentID, url, username, password)

    do return end

    print("Fetching content ID from the original document #" .. documentID .. " from Mojo")
    local contentID = fetchContentID(url, username, password, documentID)

 

    print("Fetching content for content #" .. contentID .. " enveloped by document #" .. documentID .. " from Mojo")
    fetchOriginalDocument(url, username, password, contentID)

 

    print("Preparing JSON file for Mojo")
    prepareJSONFile(outputFileName)

 

    print("Pushing new content #" .. contentID .. " enveloped by document #" ..
    documentID .." into Mojo") pushNewDocument(url, username, password, contentID)

 

    print("Done")
end

 

 

 

--
-- Do all stuff
--
process(arg)

 

 

 

--
-- Finito
--
