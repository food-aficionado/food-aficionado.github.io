import requests
import os
from datetime import datetime
import openai
import re
import logging
import urllib
import json
import time
import base64
import glob
from datetime import datetime, timedelta
import random

class APIHandler:
    BASE_URL = 'http://localhost:3000/api/v1/ingredients'

    def get_ingredients(self, page):
        url = f'{self.BASE_URL}/?page={page}'
        response = requests.get(url)
        return response.json()

    def get_ingredient_details(self, ingredient_id):
        url = f'{self.BASE_URL}/{ingredient_id}'
        response = requests.get(url)
        return response.json()

    def update_ingredient(self, id, ingredient):
        url = f'{self.BASE_URL}/{id}'
        headers = {'Content-Type': 'application/json'}
        response = requests.put(url, headers=headers, json=ingredient)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            logging.error(f"Invalid ingredient ID or request body: {response.text}")
            return None
        else:
            logging.error(f"Error occurred: {response.text}")
            return None

    def get_ingredient_by_name(self, name):
        # Encode the ingredient name
        ingredient_name = urllib.parse.quote(name)
        get_url = f'{self.BASE_URL}/by_name/{ingredient_name}'
        headers = {'Content-Type': 'application/json'}
        get_response = requests.get(get_url, headers=headers)
        if get_response.status_code == 200 and get_response.json():
            return get_response.json()
        elif get_response.status_code == 404:
            return None
        else:
            logging.error(f"Error occurred: {get_response.text}")
            return None



class TextProcessor:
    def strip_images(self, text):
        return re.sub(r'!\[.*?\]\(.*?\)', '', text)


class OpenAIHandler:
    def __init__(self, api_key):
        self.api_key = api_key
        openai.api_key = self.api_key

    def generate_tags(self, content, text_processor):
        prompt = f"Please analyze the following content and provide relevant tags for a blog post. The tags should be in a simple, comma-separated list with no additional formatting or characters. Content: {text_processor.strip_images(content)}"
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=30
        )
        tags = response.choices[0].text.strip()
        return [tag.strip() for tag in tags.split(",")]
    
    def generate_categories(self, content, text_processor):
        prompt = f"Please analyze the following content and provide up to 3 relevant categories for a blog post. The categories should be in a simple, comma-separated list with no additional formatting or characters. Content: {text_processor.strip_images(content)}"
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=30
        )
        tags = response.choices[0].text.strip()
        return [tag.strip() for tag in tags.split(",")]
    
    def summarize_text(self, text):
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Please summarize the following text in one sentence: {text}",
            max_tokens=60
        )
        return response.choices[0].text.strip()
    
class BlogCreator:
    def __init__(self, openai_handler, text_processor):
        self.openai_handler = openai_handler
        self.text_processor = text_processor

    def extract_nutrients(self, ingredient_details):
        nutrients = ingredient_details['nutrients']
        result = []
        for nutrient in nutrients:
            name = nutrient['nutrient']['name']
            amount = nutrient['nutrientAmount']
            unit = nutrient['nutrientUnit']
            ingredientAmount = nutrient['ingredientAmount']
            ingredientUnit = nutrient['ingredientUnit']
            result.append({
                'name': name,
                'amount': amount,
                'unit': unit,
                'ingredientAmount': ingredientAmount,
                'ingredientUnit': ingredientUnit
            })
        return result
    
    def create_blog_page(self, ingredient_details, image_handler):
        blog_title = ingredient_details['name'].capitalize()
        description = ingredient_details['description']
        description_without_images = self.text_processor.strip_images(description)

        facts = ingredient_details['facts']
        # date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        random_days_in_past = random.randint(1, 365 * 1)  # Up to 1 years in the past
        random_time_in_past = timedelta(days=random_days_in_past)
        past_date = datetime.now() - random_time_in_past
        date = past_date.strftime("%Y-%m-%d %H:%M:%S")
        summary = self.openai_handler.summarize_text(description)
        tags = self.openai_handler.generate_tags(description, self.text_processor)
        tags_line = ", ".join(tags)
        # Removing the prefix "tags:" or "Tags:" and any non-alphanumeric characters except comma and space
        tags_line = re.sub(r'^(tags:|Tags:)\s*', '', tags_line)
        tags_line = re.sub(r'[^\w\s,]', '', tags_line)
        # Removing extra spaces and ensuring only one space after each comma
        tags_line = re.sub(r'\s*,\s*', ', ', tags_line)
        # Removing trailing comma and trimming leading or trailing spaces
        tags_line = tags_line.rstrip(', ').strip()

        categories = self.openai_handler.generate_categories(description, self.text_processor)
        categories_line = ", ".join(categories)
        # Removing the prefix "tags:" or "Tags:" and any non-alphanumeric characters except comma and space
        categories_line = re.sub(r'^(tags:|Tags:|categories:|Categories:)\s*', '', categories_line)
        categories_line = re.sub(r'[^\w\s,]', '', categories_line)
        # Removing extra spaces and ensuring only one space after each comma
        categories_line = re.sub(r'\s*,\s*', ', ', categories_line)
        # Removing trailing comma and trimming leading or trailing spaces
        categories_line = categories_line.rstrip(', ').strip()

        nutrients = self.extract_nutrients(ingredient_details)

        prompt = f"A high-quality, realistic photograph of {blog_title}, capturing its vibrant color, distinctive texture, and appearance when freshly prepared or used in culinary dishes. The image should reflect the unique characteristics and essence of {blog_title} as often depicted in culinary art and literature. It must resonate with the authentic culinary experience of {blog_title}, showcasing it as a vital ingredient in recipes. This image will serve as a visually appealing accompaniment to a detailed blog article focusing on the culinary applications, history, and cultural significance of {blog_title}."
        imagePath = f'./assets/images/{ingredient_details["id"]}.png'
        b64images = image_handler.generate_image(prompt, 1, "512x512", "b64_json")
        if b64images is None:
            b64image = None
            logging.info(f"Failed to generate image for {blog_title}")
        elif len(b64images) == 0:
            b64image = None
            logging.info(f"Failed to generate image for {blog_title}")
        else:
            b64image = b64images[0]
            with open(imagePath, 'wb') as file:
                file.write(base64.b64decode(b64image))
            logging.info(f"Generated image for {blog_title}")
    
        tags_line = ','.join(filter(bool, map(str.strip, tags_line.split(','))))
        categories_line = ','.join(filter(bool, map(str.strip, categories_line.split(','))))
        summary = blog_title.replace('"', '\\"')
        blog_title = summary.replace('"', '\\"')

        content = f"""---
layout: post
title: "{blog_title}"
description: "{summary}"
tags: [sticky, featured, {tags_line.lower()}]
categories: [{categories_line.lower()}]
nutrients: {json.dumps(nutrients)}
image: "{imagePath}"
related_posts: true
author: "food-aficionado"
---
{description_without_images}

{facts}
"""
        filename = f'./_posts/{date.split()[0]}-{blog_title.replace(" ", "_").lower()}.md'
        with open(filename, 'w') as file:
            file.write(content)



class ImageHandler:
    def generate_image(self, prompt, n_images=1, size="1024x1024", response_format="b64_json"):
        logging.info(f"Generating image")
        url = "https://api.openai.com/v1/images/generations"
        headers = {"Content-Type": "application/json",}
        data = {"prompt": prompt, "n": n_images, "size": size, "response_format": response_format}
        response = self.post_with_backoff(url, headers, data)
        base64_images = []

        if response and response.status_code == 200:
            image_data_list = response.json()['data']
            for img_data in image_data_list:
                img_base64 = img_data['b64_json']
                base64_images.append(img_base64)
            logging.info(f"Images retrieved in base64 format.")
        else:
            logging.info(f"Request failed for generate image")
            return None

        return base64_images

    def post_with_backoff(self, url, headers, data, max_retries=4):
        for _ in range(max_retries):
            headers['Authorization'] = f"Bearer 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"
            response = requests.post(url, headers=headers, data=json.dumps(data))

            if response.status_code == 200 and response.content:
                return response
            elif response.status_code == 400:
                return None
            elif response.status_code in [429, 402, 503]:
                logging.info(response.json())
                logging.info(f"Rate limit reached. Retry after 2 seconds.")
            else:
                logging.info(f"Unexpected status code {response.status_code}. Retry with a new key after 2 seconds.")
                logging.info(f"Response: {response.text}")

            time.sleep(1)

        logging.info(f"Failed to get a successful response after {max_retries} attempts, exiting.")
        return None

class IngredientBlogApp:
    def __init__(self):
        self.api_handler = APIHandler()
        self.text_processor = TextProcessor()
        self.openai_handler = OpenAIHandler("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")
        self.image_handler = ImageHandler()
        self.blog_creator = BlogCreator(self.openai_handler, self.text_processor)

    def main(self):
        current_page = 40
        total_pages = 300
        os.makedirs('./_posts', exist_ok=True)

        for page in range(current_page, total_pages + 1):
            print(f"Processing page {page}")
            ingredients_data = self.api_handler.get_ingredients(page)
            ingredients = ingredients_data['ingredients']

            for ingredient in ingredients:
                ingredient_name = ingredient['name']
                pattern = f'_posts/*-{ingredient_name.replace(" ", "_").lower()}.md'
                if glob.glob(pattern):
                    print(f"File for {ingredient_name} already exists. Skipping.")
                    continue
                print(f"Processing {ingredient_name}")
                ingredient_id = ingredient['id']
                ingredient_details = self.api_handler.get_ingredient_details(ingredient_id)
                self.blog_creator.create_blog_page(ingredient_details, self.image_handler)
                print(f"Blog page created for {ingredient_name}")


if __name__ == '__main__':
    app = IngredientBlogApp()
    app.main()
