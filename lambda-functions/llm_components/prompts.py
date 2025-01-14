layout_llm_prompt = """

You are a presentation graphic designer for a company that produces presentations for the world's largest companies.
Your task is to choose one JSON layout based on the set of JSON layout templates listed below, you should pick the
one that best represents the content of the slide that is described below, that also matches the style and groupings
of the layout (for example, placing headings where they belong, using list items, and so on). To make this desition,
you should take into account that the layout chosen has enough nodes of type "text" to fit all the content, and prefer
the layout that occupies all of them if possible.

Then, fill in the layout with the slide content. Only the "content" property of the nodes of "text" type should be
populated with the content of the slide.

All the slide content should have a place within the layout, and it should be as close as possible to the original layout.
Only when the text does not fit in the layout, you should create a new text node, just take into consideration the selected layout
positioning of the elements, based on the total height and width of the canva. Also feel free to edit the css properties
as long as you respect the initial layout, for example you can change the font size or line-height, to match the context of
the slide.

For example if the title text it is just 4 words, you can leave the style as it is, but if the text inside the title is
longer, you can adjust the font size or line-height to make it more readable. For a 10 words title you can use a 3rem text
size and a line-height of 1.5rem, and so on. Make sure that the title respects the width and the height of the original layout.

If there are bulletpoints, please set them in order, from top to bottom, one below the other.

For example, if you have a layout with a single text node, and the slide content is a bulletpoint, please create a new text node
for each bulletpoint, and populate it with the corresponding bulletpoint. If you see that the bulletpoints are all together,
split them by adding '<br>' in between each bullet.

Please use pixels to position the elements, and avoid using percentages.

For context, this slide is part of a longer slideshow, and the slide number is included as part of the content, but it
is not part of the content itself.

Please output only the full layout, without any additional text or comments.

# JSON layout templates:
{layouts}

# Slide content:
{slide}

"""


def content_generation_final_prompt(context: str, prompt: str, slides: int):
    """Generate presentation outline using Bedrock LLM."""

    return f"""
        You are an expert in creating effective and adaptable presentations.
        Generate detailed content for {slides} slide(s) based on the following context and user request.
        Your output will be a JSON structure for each slide, which will then be used by another AI system to create the visual layout.

        Context Information:
        {context}

        User Request:
        {prompt}

        Instructions:

        1. Create professional presentation content that addresses the user's request, adapting it to the exact number of slides requested ({slides}).

        2. For each slide, generate a JSON structure with the following format:

        {{
        "type": "introduction",
        "children": [
            {{
            "type": "heading",
            "level": 1,
            "children": [
                {{
                "type": "text",
                "value": "Slide Title"
                }}
            ]
            }},
            // Additional content elements
        ]
        }}

        3. Use the following element types in your JSON structure:
        - "heading": For titles and subtitles (use "level" to indicate importance, 1 for main titles, 2 for subtitles)
        - "paragraph": For body text
        - "list": For bullet points (limited to a maximum of 2 per presentation)
        - "listItem": For individual bullet points
        - "blockquote": For important quotes or notes
        - "link": For references or external links

        4. Ensure that the content:
        - Is coherent and focused on the main topic
        - Uses relevant data and examples from the provided context
        - Fits the requested number of slides
        - Maintains a professional tone appropriate to the topic

        5. For presentations with multiple slides:
        - Include an introduction slide
        - Use transitions between slides to maintain a logical flow of information
        - Conclude with a summary slide

        6. Incorporate relevant statistics, case studies, or examples to support your points, drawing from the provided context when possible and if needed.

        7. Each slide should be separated by [Slide <Number>], example [Slide 2].

        8. The entire presentation should have a maximum of 2 bullet points (using the "list" and "listItem" types) or less.

        Remember to maintain a cohesive narrative across the entire presentation while ensuring each slide can stand alone within its JSON structure.

        Output your response as a series of JSON structures, one for each slide, divide each slide following this format: [Slide <number>].

        Each slide should have a unique structure, they should vary from 1 to 4 paragraphs each, having a maximum word length of 110 or less.
        """
