from pathlib import Path
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor
from scrapy.signalmanager import dispatcher
from scrapy import signals
import json

class WikiSpider(scrapy.Spider):
    name = "datascraper"

    def __init__(self, start_url=None, *args, **kwargs):
        super(WikiSpider, self).__init__(*args, **kwargs)
        self.start_urls = [start_url]
        self.results = []

    def start_requests(self):
        urls = self.start_urls
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        # main_title = response.css("main.mw-body h1 ::text").get()
        # # body_content = response.css("div .mw-body-content".get())
        # item =  {"main_title": main_title}
        # self.results.append(item)

        sub_titles = response.xpath("//div[@class='mw-body-content']//h2")
        
        for title in sub_titles:
            flag = False
            images, text_content, tables, links = [], [], [], []

            title_text = title.css("::text").get()  # Text if sub title
            div_tag = title.xpath("..")[0]  # Parent div tag
            following_tags = div_tag.xpath('following-sibling::*')
            for tag_element in following_tags: # Iterating through all the following tags to get the contents related to the heading
                if tag_element.root.tag == 'div' and tag_element.css('::attr(class)').get() == 'mw-heading mw-heading2':  # Condition to break the loop when the next heading is reached
                    flag = True
                    break
                elif tag_element.root.tag == 'figure':
                    images.append(tag_element.css("a img::attr(src)").get())
                elif tag_element.root.tag == 'p':
                    text_content.append(tag_element.css("::text").getall())
                elif tag_element.root.tag == 'table' and tag_element.css('::attr(class)').get() == "wikitable":
                    tables.append(self.extract_table_data(tag_element))
                
            item = {
                "title": title_text,
                "text_content": self.process_text_content(text_content),
                "images": images,
                "table": tables
            }
            self.results.append(item)
            if flag == True:
                continue
              # Store in spider's results list
        return item  #


    def extract_table_data(self, table_tag):
        tbody = table_tag.css("tbody")
        table_dict = {}
        header = []
        for val in tbody.xpath("tr")[0].xpath("th"): # Getting the headers
            text = val.css("::text").get().strip()
            header.append(text)
            table_dict[text] = []  # Initializing the header as key to dict and value as a list

        for col in range(len(header)-1): # Getting header data
            for row in range(1, len(tbody.xpath("tr"))):
                table_dict[header[col+1]].append(tbody.xpath("tr")[row].xpath("td")[col].css("::text").get().strip())

        for row in range(1, len(tbody.xpath("tr"))):  # Getting index data
            table_dict[header[0]].append(tbody.xpath("tr")[row].xpath("th")[0].css("::text").get().strip())

        return table_dict
        


    def process_text_content(self, data):
        flattened_sentence = "".join([item for sublist in data for item in (sublist if isinstance(sublist, list) else [sublist])])
        flattened_sentence = " ".join(flattened_sentence.split())
        return flattened_sentence

def scrape_url(url):
    results = []
    
    def crawler_results(signal, sender, item, response, spider):
        results.extend(spider.results)
    
    process = CrawlerProcess(settings={
        'LOG_ENABLED': False,
        'USER_AGENT': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
    })
    
    dispatcher.connect(crawler_results, signal=signals.item_scraped)
    
    process.crawl(WikiSpider, start_url=url)
    process.start()
    
    return results

def convert_table_to_markdown(table):
    """Converts a list of table dictionaries into Markdown format."""
    markdown_tables = []
    
    for table_dict in table:
        headers = table_dict.keys()
        rows = zip(*table_dict.values())  # Transpose rows
        
        # Create Markdown table
        markdown_table = f"| {' | '.join(headers)} |\n"
        markdown_table += f"|{' | '.join(['---'] * len(headers))}|\n"
        for row in rows:
            markdown_table += f"| {' | '.join(row)} |\n"
        
        markdown_tables.append(markdown_table)
    
    return "\n\n".join(markdown_tables)

def convert_json_to_markdown(data):
    """Converts JSON list to properly formatted Markdown content."""
    markdown_content = []
    
    for item in data:
        markdown_content.append(f"# {item['title']}\n")
        markdown_content.append(item['text_content'] + "\n")
        if item.get("images"):
            for img in item["images"]:
                markdown_content.append(f"![Image]({img})\n")
        # Add tables
        if item.get("table"):
            markdown_content.append(convert_table_to_markdown(item["table"]))
    return "\n\n".join(markdown_content)