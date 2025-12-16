This chapter covers:
- Assembling a crew of specialized agents
- Designing specific tasks for the agents
- How to use knowledge in crews
- Using short-term, long-term, and entity memory in crews
- Delegation and the different process types of crews

After implementing a single agent in the last chapter, we will explore CrewAI's most important feature here: assembling multiple highly specialized agents into a crew and having them work on tasks in a collaborative way.

Crews are incredibly versatile and can be configured and run in multiple ways. We will look into how tasks can be assigned to specific agents, what ways there are of agents working together, how crews can leverage knowledge and memory, as well as how we can use existing tools and even implement new tools to be used by agents ourselves.

## Initializing the project

In this chapter, we will build a crew—a group of highly specialized agents working together—that can automate the entire SEO process for us.

SEO (Search Engine Optimization) is the practice of improving a site's visibility in unpaid search results (e.g., in Google, Bing, DuckDuckGo, or other search engines) so more qualified people find (and convert on) your company's website. There are a few different variants of SEO, such as:
- **Technical SEO:** Focuses on enhancing website visibility and accessibility by optimizing crawlability, improving site speed, ensuring mobile-friendliness, and implementing structured data to help search engines better understand the content.
- **On-page SEO:** Involves creating high-quality, valuable content, optimizing titles and meta tags, and incorporating internal links to improve user experience and search engine rankings.
- **Off-page SEO:** Emphasizes building high-quality backlinks through outreach, mentions, and collaborations, which signal to search engines the website's authority and relevance, thereby increasing its credibility and ranking potential.

In this project, we're focusing specifically on on-page SEO by writing high-quality blog posts that target specific keywords. We can automate the process by starting with a description of what our own business does, and then assembling a list of direct or indirect competitors. For each competitor, we research what keywords they currently rank for in Google, and then build a list of valuable keywords to use ourselves. We then pick one or more keywords to write about, do some research about the topic and how it relates to our company, and then write a very specific and detailed blog post about this topic.

![[crew-seo-process.excalidraw]]

To get started, navigate to your projects directory in your terminal, and create a new project using the `crewai` command:

```
crewai create crew seo_crew
```

During this process, you will be asked which model provider to use and which default model to use. You can select the OpenAI provider and choose the `gpt-4o` model here. You will also be prompted for an OpenAI API key, which you can get from the OpenAI Platform website.

If everything went well, you should see a folder named `seo_crew`, which includes a boilerplate crew. In the `.env` file, you should see the API key that you previously provided. If you want to change this later—or use a different model provider—you can do so directly in this file.

You can try to run this to see if everything went well:

```
crewai run
```

If you encounter any errors at this step, please refer to Appendix A to ensure your system is correctly set up for CrewAI. You can also get help on the official CrewAI forum.

Once again, we will need the additional packages `crewai-tools` (which contains a list of third-party tools and integrations for CrewAI) and `pydantic` (the most popular schema and validation library for Python), so make sure to install those as well:

```
uv add crewai crewai-tools pydantic
```

The newly created directory is structured as follows:
- The `.venv`  directory is automatically created by `uv` (which is the project manager that `crewai` uses) and contains the configuration of your environment, as well as all installed dependencies.
- The `.env` file contains your secrets, mainly API keys. The data in there is sensible and should not be committed to version control; that's why this file is already listed in the `.gitignore` file, which tells Git to ignore and not index it. Instead, every developer working on the project has to provide those for themselves. You should create a `.env.example` file that contains example values, which makes it easier to get started if you are working with other developers on the same project.
- In the `pyproject.toml` file you can see (and change) the name of the project, its version, and description, as well as declare all dependencies used by it.
- While the `pyproject.toml` file declares the project's dependencies (and usually includes a version range to use), and the exactly installed versions are locked in the `uv.lock` file. When using this file, `uv` will always install exactly the same versions of all dependencies. This is very important for a project, especially when working on it together, and the file should be placed under version control.
- All main application code can be found in the `src/seo_crew` directory. The `main.py` file includes a boilerplate setup that exposes the crew's `run`, `train`, `replay`, and `test` methods. Those are also referenced in the `pyproject.toml` file, and enable the `crewai` command to easily run the crew.
- In the folder `src/seo_crew/config` there are two files `agents.yaml` and `tasks.yaml`. Those include the definitions of the crew's agents and tasks in the YAML format. This is an optional way of defining your agents, but it's used as the default in new CrewAI applications.
- In the `src/seo_crew/tools` folder, you can see a custom demo tool, which can be used by the agents in your crew. Should you want to create your own tools for agents to use, this is the folder to put them in.
- In the `src/seo_crew/crew.py` file, the crew itself is defined. As you can see, this definition references the two YAML files mentioned previously. In here, you can make all configurations for your tasks, agents, tools, and the crew itself.

Let's now get started implementing the first agent in this project.
## Creating the keyword researcher

The first agent is responsible for researching a list of keywords that competitors already rank for. To achieve this task, it will need access to a tool to search the web. We can, once again, use the `SerperDevTool` for this.

Serper is a third-party service that offers an API (with a generous free plan) that exposes Google search results in a structured way. If you haven't yet, make sure to create an account for it on [serper.dev](https://www.serper.dev), then create an API key, and then save this key in your `.env` file as `SERPER_API_KEY`. The Serper API has a generous free plan, which should suffice for this example.

To give the agent some direction, we need to define its three narrative pillars. The role defines the agent's function and expertise within its crew, the goal describes the individual objective that guides the agent's decision-making, and the backstory provides context and personality to the agent.

![[keyword-researcher-agent.excalidraw]]

There are two ways of defining an agent in code, one of which we already looked at in the first chapter of the book. An agent can be defined in code directly.

```python
from crewai import Agent

keyword_researcher = Agent(
  role="Keyword researcher",
  goal="Extract high-value keyword candidates...",
  backstory="You are an experienced SEO pro who..."
)
```

Alternatively, and this is now the default for new CrewAI projects, you can use the YAML configuration instead. For this, you have two YAML files for each crew, `agents.yaml` and `tasks.yaml`. This provides a cleaner and more maintainable way to define both agents and tasks, and it has the added benefit that your prose (prompts and instructions in natural language) is kept separate from your application logic.

To define our agent in YAML, add this to the file `src/seo_crew/config/agents.yaml`:

```yaml
keyword_researcher:
  role: >
    Keyword researcher
  goal: >
    Extract high-value keyword candidates by searching for and analyzing
    on-page content from competitors' websites.
  backstory: >
    You are an experienced SEO pro who can find other websites' secret
    ways of hacking their way into Google search results.
```

We will add the `SerperDevTool` when assembling the crew, as this is not done in the YAML configuration, but rather in the `src/seo_crew/crew.py` file.

Now, we also have to create a task to give to this agent. Tasks must provide all necessary details for their execution, including a clear description of what needs to be done, how the output should be structured, the tools to be used, the responsible agent, and more. The task description is more important than the agent's description, so always make sure to put enough effort into the exact definition of your tasks.

We use a competitor-only keyword discovery workflow: the keyword researcher runs site-restricted searches (e.g., `site:domain.com` filters in Serper) to surface a competitor's own pages that are listed on Google, then extracts its title, link, and a text snippet for it. The researcher agent then converts those signals into normalized, de-branded keyword candidates and dedupes close variants. The result is a concise, source-linked, high-signal keyword list that the topic researcher can use to choose the next best article to focus on.

We can capture this in the task description, which we write directly to the file `src/seo_crew/config/tasks.yaml`.

```yaml
keyword_research_task:
  description: >
    Extract high-value keyword candidates by searching for and analyzing
    on-page content from competitors' websites. Use the search tool provided to find all the serps for a competitor using the "site:example.com" syntax.
    Analyze the SERPs and extract the high-value keyword candidates. Usually, those can be found in the title and/or URL of the search results.
    Use the following location for the search: {country} and the specified language: {language}.
  expected_output: >
    A list of high-value keyword candidates. Format the list as a JSON array of strings, ordered from most relevant to least relevant. Ignore any keywords that we have written blog posts about already.
  agent: keyword_researcher
```

As you can see, we are using variables for both country and language using the curly braces syntax. This way, when invoking the crew, we can pass them in and always target our efforts to a specific location. At runtime, they will be replaced with their specific values.

Those inputs can be passed into a crew run like this:

```
crew.kickoff(inputs={'country': 'US', 'language': 'English'})
```
## Creating the researcher

Now, let's build the second agent in this project. This agent's task is to first choose one or more keywords to target based on the keyword researcher's results, then conduct research on this topic and present its findings in a somewhat structured way. This agent is very similar to the standalone agent we built in the first chapter.

We can once again use the Serper tools `SerperDevTool` and `SerperScrapeWebsiteTool` to give our agent access to Google search results, and to actually navigate to the sites and read their content, which is very important when we want to inspect what our competitors are writing about.

![[seo-researcher-agent.excalidraw]]

We can write down the three narrative pillars in the file `src/seo_crew/config/agents.yaml`.

```yaml
topic_researcher:
  role: >
    Topic researcher
  goal: >
    Based on the keyword candidates, choose a topic for a single blog post that incorporates one or more of the keywords.
  backstory: >
    You are an experienced researcher who is very experienced in finding rabbit holes and digging deep into the internet to find the most relevant information - the kind of information you wouldn't find in a simple surface-level Google search.
```

We also need a task that we can give to this agent. We can define it as follows:

```yaml
topic_research_task:
  description: >
    Based on the keyword candidates, choose a topic for a single blog post that incorporates one or more of the keywords. Go ahead and do some deep research on the topic, using the search and website scraping tools provided to you.
  expected_output: >
    An in-depth report on the topic. Format the report as markdown.
  agent: topic_researcher
```
## Creating the blog writer

The third and final agent for our assembly is the blog post writer, who takes the research and actually writes a blog post that is optimized for SEO. Using the narrative pillars, we can push the agent to be an absolute expert in this topic and write articles that will convert well on Google Search.

However, articles with just text can seem boring, and it's well known that an image conveys the meaning of a 1000 words. That's why we want to give our agent access to a tool to generate images to illustrate the blog posts. To do so, we can use the `DallETool` from CrewAI that ships with the `crewai-tools` package. This will use OpenAI's API endpoints with its DALL-E text-to-image model to generate images.

Here's how the tool can be initialized:

```python
from crewai_tools import DallETool #A

image_generation_tool = DallETool( #B
    size="1792x1024", #D
    n=1 #F
)

# In your crew definition
Agent(..., tools=[image_generation_tool])
```

Because this tool also uses the OpenAI API, make sure to have an OpenAI API key configured in your `.env` file, even in case you are using a different model provider, like Anthropic or X.AI.

We can test this tool manually to see if it all works as expected. For that, let's create a new file `tool_test.py` with the following content:

```py
import json
from crewai_tools import DallETool #A

image_generation_tool = DallETool( #B
    model="gpt-image-1",   #C
    size="1024x768", #D
    quality="high", #E
    n=1 #F
)

result = image_generation_tool.run(image_description="A futuristic cityscape at sunset")

print(json.dumps(result, indent=2))
```

The result will include an `image_url` property with a link to the generated image.

![[Pasted image 20251031120715.png]]
Through the runtime context, our agent will learn about our own company, the list of competitors, a prioritized list of keywords for us to use, and the prepared research from the previous step.

![[blog-writer-agent.excalidraw]]
Once again, we can put the definition of this agent into the file `src/seo_crew/config/agents.yaml` and write down its narrative pillars.

```yaml
blog_post_writer:
  role: >
    Blog post writer
  goal: >
    Based on the research that the topic researcher has done, write a highly engaging and structured blog post that incorporates one or more of the keywords chosen by the keyword and topic researchers.
  backstory: >
    You are an experienced writer who has written thousands of blog posts and who's an expert in knowing how to structure posts so they perform well on Google search.
```

And, once again, we need an accompanying task that describes exactly what we expect from the agent. We will use the language passed in to the crew execution as the language of the blog article itself.

```yaml
blog_writing_task:
  description: >
    Based on the research that the topic researcher has done, write a highly engaging and structured blog post that incorporates one or more of the keywords chosen by the keyword and topic researchers. Make sure the blog post is optimized for SEO and uses at least one of the keywords in the title.
    Use the image generation tool to generate meaningful images that convey the main ideas of the post better. Embed at least three images in the post.
  expected_output: >
    A highly engaging and structured blog post in the language {language} that incorporates one or more of the keywords chosen by the keyword and topic researchers. Format the blog post as markdown.
  agent: keyword_researcher
  output_file: blog_post.md
```

While the images generated by DALL-E are good, their style is not always consistent, which might be bad for our blog posts. For our use case, it would be beneficial if the images adhered to a distinct and specific style.

There are a lot of other text-to-image models out there, many of which are better and more controllable than OpenAI's image generation model. One of those is the FLUX.1 model by the German AI research lab [Black Forest Labs](https://bfl.ai).  FLUX is a great model, and it supports fine-tuning with LoRA.

LoRA (Low-Rank Adaptation) is a lightweight method for customizing large AI models without retraining all their weights. It works like a plug-in you attach to a model, so it can give it a new style of concept. Instead of changing the model's original weights, you train a tiny set of add-on weights that sit on key layers (in text-to-image systems like Flux, that's usually parts of the attention blocks). At generation time, the base models run as usual, and the LoRA gently nudges them toward the desired look or subject. Because these add-ons are small, they're quick to train, easy to share, and you can stack or blend multiple LoRAs for composite effects. In fact, there is an online community called CivitAI where developers and designers share self-trained model checkpoints, generated images, and much more.

Let's build a tool that takes the same input as the DALL-E tool, but instead uses the Flux model with a style LoRA to generate the image. I found this cool-looking ["retro neon style"](https://civitai.com/models/569937/retro-neon-style-fluxsdxlillustrious-xlpony?modelVersionId=747123) model on CivitAI, which I think has a very nice and distinct style that we can use for our blog posts. Feel free to choose any other Flux .1-dev compatible model that you can find.

To generate the image, we can use the [Replicate platform](https://www.replicate.com) that hosts a multitude of openly available AI models and makes them easily accessible through an API. To generate images through Replicate, you first have to sign up and create an account, and then add a payment method. The price of image generation on Replicate depends on the model and settings that you use, but with the `black-forest-labs/flux-dev-lora` model we will use, one image costs $0.032, which means you can generate 30 images for $1.

After you sign up for the service and add a credit card, you need to create an API token under ["Account Settings" > "API tokens"](https://replicate.com/account/api-tokens). Copy this token and save it as `REPLICATE_API_TOKEN` in your `.env` file.

Now, we need to install the `replicate` package into our project.

```
uv add replicate
```

Now, we can implement our new custom tool. For that, create a new file `image_tool.py` in the `src/seo_crew/tools/` folder and add the following content.

```python
from typing import Type, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import os
import replicate

class ImageGenerationToolInput(BaseModel):
    image_description: str = Field(..., description="Description of the image to generate.")

class ImageGenerationTool(BaseTool):
    name: str = "generate_image"
    description: str = (
        "Generate a custom image based on the description provided."
    )
    args_schema: Type[BaseModel] = ImageGenerationToolInput
    base_path: str = Field(default=".", description="Base path where images should be saved")

    def _run(self, image_description: str) -> str:
        outputs = replicate.run(
            "black-forest-labs/flux-dev-lora",
            input={
                "prompt": image_description + " retro_neon style",
                "num_outputs": 1,
                "aspect_ratio": "16:9",
                "image_quality": 1,
                "image_format": "jpg",
                "lora_weights": "https://civitai.com/api/download/models/747123"
            }
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = next(iter(outputs))
        filename = f"output_{timestamp}.jpg"
        filepath = os.path.join(self.base_path, filename)
        os.makedirs(self.base_path, exist_ok=True)
        with open(filepath, "wb") as file:
            file.write(output.read())

        return f"Image generated successfully: {filepath}"
```

We can now directly invoke the tool to test it. It takes one optional field to configure the base directory where the images should be saved.

```python
image_generation_tool = ImageGenerationTool(base_path="./images")
result = image_generation_tool.run(image_description="A futuristic cityscape at sunset")
print(result)
```

You should now see an output like this:

```
Using Tool: generate_image
./images/output_20251031_164749.jpg
```

In the `images/` directory, there should now be an image file that you can open. The one I generated now looks like this. I really like the style, and I could imagine this sort of aesthetic can work very well for certain kinds of startups.

![[Pasted image 20251031165608.png]]
## Loading knowledge

The user of the crew has to provide some necessary data that the crew can access at runtime, which includes the company's own name, description, and background info, as well as a list of competitors to monitor. To pass this context to the crew, we can use CrewAI's knowledge feature.

Knowledge in CrewAI is basically a built-in RAG (Retrieval Augmented Generation) layer: you attach documents (Markdown/text, CSV/JSON, PDFs, or even just raw strings) to a crew or specific agent, CrewAI chunks the content and creates embeddings for them, saves them in a vector database, and at task time, automatically retrieves the most relevant snippets with no manual tool call needed. Retrieval can be controlled with `KnowledgeConfig`, and you can store collections under custom paths.

Embedding models are AI models that turn data, like text, images, or even audio, into numerical vectors (lists of numbers). The vectors capture the meaning or semantic relationships between items so that similar things are close together in this vector space.

For example:
- The words “dog” and “puppy” might get embeddings like `[0.12, 0.98, -0.44, …]` and `[0.15, 1.01, -0.40, …]`, which are close together.
- The word **“car”** would have a very different vector, farther away.

![[embedding-model.excalidraw]]
Modern multilingual embedding models map text from different languages into the same semantic space. That means that the English word "dog", the Spanish word "perro", and the German word "Hund" all get very similar vectors. This happens because the model was trained on multilingual corpora where the same ideas appear in different languages, letting it learn shared meaning patterns.

OpenAI provides access to its own embedding models through its API. You can find an overview of their models [in their documentation](https://platform.openai.com/docs/guides/embeddings/embedding-models#embedding-models).

Currently, they are offering `text-embedding-3-small`, `text-embedding-3-large`, and the `text-embedding-ada-002` models. The `ada` model is a bit outdated, so it should only be used for backward compatibility and not for new applications. For most users, the `small` model is the perfect choice between accuracy and cost, but if accuracy is critical, then the `large` model might be worth the additional cost.

Vector databases store and index those embeddings so you can search by meaning instead of exact wording. Instead of doing `SELECT * WHERE title LIKE '%dog%'`, you can take a user query like "best family-friendly pets", turn that query into an embedding vector, and then ask the database: "Which stored vectors are closest to this one?". The database uses efficient nearest-neighbor search to find the most similar vectors very quickly. The result is semantic retrieval: even if a document never literally says "family-friendly pets", an article about "low-maintenance dogs for kids" will rank highly because its embedding sits near the query in vector space. CrewAI internally also uses query rewriting to make retrieval more precise before injecting context into prompts. This is the core of RAG: embed your knowledge base, store it in a vector database, and at question time, embed the question and retrieve the top-K nearest chunks to feed to the model.

At runtime, you attach one or more knowledge sources to either the whole crew (shared by all agents) or to specific agents. When the crew starts, CrewAI chunks your documents into retrieval‑friendly pieces, embeds each chunk with your configured embedder, and persists those embeddings to a local vector store. During task execution, CrewAI then performs semantic retrieval to automatically fetch the top‑K most relevant chunks for each prompt and injects them into the model's context. Agents automatically see crew‑level knowledge in addition to any agent‑specific sources you assign; you don't need to call a separate tool to "look up" knowledge—retrieval happens behind the scenes for each task.

You control this behavior through the `KnowledgeConfiguration`. The configuration allows you to tune several key parameters. Chunk size determines how many characters or tokens each document piece contains—smaller chunks (e.g., 200 tokens) capture fine details but may miss context, while larger chunks (e.g., 1000 tokens) preserve more context but can include irrelevant information. Chunk overlap specifies how much adjacent chunks share—for example, with a 500-character chunk size and 100-character overlap, chunk one might cover characters 0–500, chunk two covers 400–900, and so on. This overlap prevents important information from being split across chunk boundaries. Top-k controls how many chunks to retrieve per query—setting it to 3 means only the three most semantically similar chunks are injected into the prompt, while 10 provides more context at the cost of longer prompts and higher token usage. Score thresholds act as a quality filter: chunks below a certain similarity score (typically between 0.0 and 1.0) are discarded to avoid injecting irrelevant information. Finally, you can specify a custom persist path if you want to control where embeddings are stored on disk. If you don't specify an embedder, CrewAI uses your project's default embedder.

By default, CrewAI persists knowledge in a local vector database (Chroma) under a project‑specific directory in your OS’s user data location. See [the official docs](https://docs.crewai.com/en/concepts/knowledge#where-crewai-stores-knowledge-files) for platform‑specific paths.

We will need exactly two knowledge files: a markdown document that describes what our own company does and gives some context on it, and a list of competitors that we want to monitor.

For that, we can create and add two files to the directory `knowledge`:
- In `about-us.md`, we add everything there is to know about our own company, including the URL of our webpage.
- In `competitors.json`, we create a structured list of our closest competitors that we want to monitor. This can be structured as follows:

```json
[
  {
    "name": "Competitor A",
    "url": "https://www.example.com"
  }
]
```

We can then initialize knowledge sources for them like this:

```python
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.source.json_knowledge_source import JSONKnowledgeSource

about_us_md = TextFileKnowledgeSource(file_paths=["knowledge/about-us.md"])
competitors_json = JSONKnowledgeSource(file_paths=["knowledge/competitors.json"])

knowledge_config = KnowledgeConfig(results_limit=30, score_threshold=0.4)
```

Those knowledge sources can be attached at either the agent level or the crew level, so every agent in the crew has automatic access to them.

```python
topic_researcher = Agent(
  [...]
  knowledge_sources=[company_md, competitors_csv],
  knowledge_config=knowledge_config
)

crew = Crew(
  [...]
  knowledge_sources=[company_md, competitors_csv]
  knowledge_config=knowledge_config
)
```

By default, CrewAI uses Chroma as a local, embedded vector database. Chroma is an open-source vector database written in Python that's designed to be lightweight and easy to embed directly into applications. Unlike traditional databases that store rows and columns, Chroma stores high-dimensional vectors (embeddings) and provides efficient similarity search capabilities. When CrewAI persists knowledge to Chroma, it creates collections—logical groupings of vectors with associated metadata. Each knowledge scope gets its own collection—crew‑level knowledge is stored in one collection, while each agent's knowledge lives in a separate collection named after the agent's role. This separation maintains clear boundaries: you can update or clear one collection without affecting the others. The persisted data lives under a project‑specific directory in your OS's user data location (typically `~/.local/share/CrewAI/{project}/knowledge/` on Linux, `~/Library/Application Support/CrewAI/{project}/knowledge/` on macOS, and `C:\Users\{username}\AppData\Local\CrewAI\{project}\knowledge\` on Windows), which allows knowledge to survive restarts and be reused across runs without re‑embedding the same files.

Chroma uses in-memory indexing for fast queries and persists data to disk using SQLite for metadata and a custom format for vectors. When you query knowledge, Chroma loads the relevant collections into memory, performs approximate nearest neighbor search using optimized algorithms, and returns the most similar vectors along with their associated text chunks and metadata. For small to medium-sized knowledge bases (up to hundreds of thousands of vectors), this local approach is both fast and convenient—no network latency, no external services to manage, and no additional costs.
## Assembling the crew

Now comes the exciting part of putting all the pieces together and assembling a crew of specialist agents. There are basically two ways of doing so: using the YAML configuration and decorators, or using direct code definitions. Both are valid and have their pros and cons, but the CrewAI team recommends using the YAML configuration + decorators variant, which is also the default when you are creating a new crew.

This approach leverages the power of decorators to automatically collect and organize your agents and tasks, making the code cleaner and more maintainable. The decorators handle the complexity of wiring everything together, so you can focus on defining what your agents and tasks do rather than how they're assembled.

Let's build our crew step by step, starting with the foundation.

First, we'll create the basic class structure. We need to import the necessary classes from CrewAI and the project decorators, as well as any tools our agents will use. Then we create a class decorated with `@CrewBase` and define the paths to our YAML configuration files:

```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from seo_crew.tools.image_generation_tool import ImageGenerationTool

@CrewBase
class SeoCrew():
  agents_config = 'config/agents.yaml'
  tasks_config = 'config/tasks.yaml'
```

The `@CrewBase` decorator is what makes this class special - it provides the infrastructure that automatically collects all agents and tasks defined in this class. The `agents_config` and `tasks_config` attributes point to our YAML files where we've defined the core characteristics of each agent and task.

Now we'll add our agents. Each agent is defined as a method decorated with `@agent`. The decorator automatically registers this method, and when the crew is assembled, all agents decorated with `@agent` are collected into a `self.agents` list that we can reference later. Each agent method returns an `Agent` instance, and we use the `config` parameter to load the agent's configuration from our YAML file. We also specify any tools the agent needs to perform its role:

```python
@CrewBase
class SeoCrew():
  [...]

  @agent
  def keyword_researcher(self) -> Agent:
    return Agent(
      config=self.agents_config['keyword_researcher'],
      verbose=True,
      tools=[SerperDevTool()]
    )

  @agent
  def topic_researcher(self) -> Agent:
    return Agent(
      config=self.agents_config['topic_researcher'],
      verbose=True,
      tools=[SerperDevTool(), SerperScrapeWebsiteTool()]
    )

  @agent
  def blog_post_writer(self) -> Agent:
    return Agent(
      config=self.agents_config['blog_post_writer'],
      verbose=True,
      tools=[ImageGenerationTool(base_path="./images")]
    )
```

Notice how each agent can have different tools assigned to it based on its specific responsibilities. The keyword researcher only needs search capabilities, while the topic researcher needs both search and website scraping. The blog post writer, on the other hand, needs our custom image generation tool to create visual content for the blog posts.

Next, we'll add our tasks. Similar to agents, each task is defined as a method decorated with `@task`. The decorator automatically collects all tasks into a `self.tasks` list. Each task method returns a `Task` instance, configured from our YAML file:

```python
@CrewBase
class SeoCrew():
  [...]

  @task
  def keyword_research_task(self) -> Task:
    return Task(
      config=self.tasks_config['keyword_research_task'],
    )

  @task
  def topic_research_task(self) -> Task:
    return Task(
      config=self.tasks_config['topic_research_task'],
    )

  @task
  def blog_writing_task(self) -> Task:
    return Task(
      config=self.tasks_config['blog_writing_task'],
    )
```

The task definitions reference our YAML configuration files, where we've specified the task descriptions, expected outputs, and which agent is assigned to each task. This separation of configuration from code makes it easy to modify task details without changing the Python code.

Finally, we'll define the crew itself. The `@crew` decorator is what brings everything together. It automatically collects all the agents and tasks we've defined (via the `@agent` and `@task` decorators) and makes them available as `self.agents` and `self.tasks`. In the crew method, we simply reference these collected lists and pass them to the `Crew` constructor:

```python
@CrewBase
class SeoCrew():
  [...]

  @crew
  def crew(self) -> Crew:
    return Crew(
      agents=self.agents,
      tasks=self.tasks,
      verbose=True,
    )
```

The magic of this approach is that `self.agents` and `self.tasks` are automatically populated by the decorators - you don't need to manually list them. This means that if you add a new agent or task method with the appropriate decorator, it will automatically be included in the crew. The `verbose=True` parameter ensures we get detailed output about what the crew is doing during execution.

Then, we will attach the knowledge source that we prepared earlier:

```python
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.source.json_knowledge_source import JSONKnowledgeSource
from crewai.knowledge.knowledge_config import KnowledgeConfig

about_us_md = TextFileKnowledgeSource(file_paths=["about-us.md"])
competitors_json = JSONKnowledgeSource(file_paths=["competitors.json"])

knowledge_config = KnowledgeConfig(results_limit=30, score_threshold=0.4)

@CrewBase
class SeoCrew():
  [...]

  @crew
  def crew(self) -> Crew:
    return Crew(
      agents=self.agents,
      tasks=self.tasks,
      verbose=True,
      knowledge_sources=[about_us_md, competitors_json],
      knowledge_config=knowledge_config
    )
```

By attaching it at the crew level, every agent automatically gets access to this knowledge, should they need it.

Alternatively, the same crew configuration in direct code definition could look like this:

```python
class DirectCodeSeoCrew:
  def keyword_researcher(self) -> Agent:
    return Agent(
      role="Keyword researcher",
      goal="Extract high-value keyword candidates...",
      backstory="You are an experienced SEO pro who...",
      verbose=True,
      tools=[SerperDevTool()]
    )

  def topic_researcher(self) -> Agent:
    return Agent(
      role="Topic researcher",
      goal="Based on the keyword candidates, ...",
      backstory="You are an experienced researcher who is...",
      verbose=True,
      tools=[SerperDevTool(), SerperScrapeWebsiteTool()]
    )

  def blog_post_writer(self) -> Agent:
    return Agent(
      role="Blog post writer",
      goal="Based on the research that the topic researcher has done, ...",
      backstory="You are an experienced writer who ...",
      verbose=True,
      tools=[ImageGenerationTool(base_path="./images")]
    )

  def keyword_research_task(self) -> Task:
    return Task(
      description="Extract high-value keyword candidates by ...",
      expected_output="A list of high-value keyword candidates. ...",
      agent=self.keyword_researcher()
    )

  def topic_research_task(self) -> Task:
    return Task(
      description="Based on the keyword candidates, ...",
      expected_output="An in-depth report on the topic. ...",
      agent=self.topic_researcher()
    )

  def blog_writing_task(self) -> Task:
    return Task(
      description="Based on the research that the topic researcher has done,...",
      expected_output="A highly engaging and structured blog post...",
      agent=self.blog_post_writer()
    )

  def crew(self) -> Crew:
    return Crew(
      agents=[
        self.keyword_researcher(),
        self.topic_researcher(),
        self.blog_post_writer()
      ],
      tasks=[
        self.keyword_research_task(),
        self.topic_research_task(),
        self.blog_writing_task()
      ],
      verbose=True,
      knowledge_sources=[about_us_md, competitors_json],
      knowledge_config=knowledge_config
    )

```

As you can see, they are not that different from each other. I would recommend the first variant to everyone starting out building with CrewAI, but the second variant can come in handy when you are trying to dynamically create crews.

## Understanding Process Types

When assembling a crew, one of the most important decisions you'll make is choosing the process type. The process type determines how tasks are orchestrated and executed by your agents. CrewAI offers two process types, each with distinct characteristics and use cases.

### Sequential Process (Default)

Sequential is the default process type in CrewAI. When using this process, tasks are executed one after another in the exact order they are defined in your tasks list. Each task must complete successfully before the next one begins, ensuring a predictable, linear workflow.

In our SEO crew, this means:
1. The keyword researcher completes its task first
2. Only after that finishes, the topic researcher begins its work
3. Finally, the blog post writer starts once the research is done

This is perfect for workflows where each step depends on the output of the previous one—exactly like our SEO pipeline, where we need keywords before we can research topics, and we need research before we can write the blog post.

To explicitly set sequential processing (which is the default anyway), you can add it to your crew definition:

```python
@crew
def crew(self) -> Crew:
  return Crew(
    [...]
    process=Process.sequential,
  )
```

### Hierarchical Process

Hierarchical process introduces a manager agent that coordinates task execution. Instead of tasks running in a fixed sequence, a manager agent evaluates the workload and dynamically delegates tasks to other agents based on their capabilities and availability. This emulates traditional organizational structures where a manager assigns work to team members.

This process type is ideal for:
- Complex workflows where task order might need adjustment
- Scenarios requiring dynamic task assignment
- Cases where validation and quality control are critical

To use hierarchical processing, you need to specify a `manager_llm` (which will automatically create a manager agent with the same LLM configuration as your crew) or create a custom `manager_agent`:

```python
@crew
def crew(self) -> Crew:
  return Crew(
    agents=self.agents,
    tasks=self.tasks,
    process=Process.hierarchical,
    manager_llm="gpt-5",
    verbose=True
  )
```

Alternatively, you can create a custom manager agent if you want more control over its role and behavior:

```python
@agent
def manager(self) -> Agent:
  return Agent(
    role="Project Manager",
    goal="Coordinate and delegate tasks efficiently",
    backstory="An experienced manager who excels at task coordination",
    verbose=True
  )

@crew
def crew(self) -> Crew:
  return Crew(
    agents=self.agents,
    tasks=self.tasks,
    process=Process.hierarchical,
    manager_agent=self.manager(),  # Use a custom manager agent
    verbose=True
  )
```

## Enabling Delegation for Agent Collaboration

While process types control the overall orchestration strategy, delegation enables agents to communicate and collaborate directly with each other during task execution. Delegation allows an agent to ask questions, request clarification, or assign follow-up work to another agent—even when using sequential processing.

By default, agents cannot delegate tasks or ask questions to other agents. To enable this capability, you need to set `allow_delegation=True` for the agent that should be able to delegate, and optionally specify which other agents it can delegate to using the `allowed_agents` parameter.

### Enabling Follow-Up Questions: Blog Writer to Researcher

In our SEO crew, we want the blog post writer to be able to ask follow-up questions to the topic researcher if something in the research report is unclear or if more specific information is needed. This makes the collaboration more dynamic and ensures the writer can get clarification without starting over.

To enable this, we need to modify our blog post writer agent to allow delegation:

```python
@agent
def blog_post_writer(self) -> Agent:
  return Agent(
    config=self.agents_config['blog_post_writer'],
    verbose=True,
    tools=[ImageGenerationTool(base_path="./images")],
    allow_delegation=True,  # Enable delegation for this agent
    allowed_agents=['Topic researcher']  # Can only delegate to the topic researcher (matches the role name)
  )
```

The `allowed_agents` parameter accepts a list of agent role names (as strings) or agent instances. Here, we're using the role name `'Topic researcher'` which matches the role defined in our YAML configuration. This approach works well with the decorator pattern and ensures the agent reference is resolved at runtime. Alternatively, you can pass agent instances directly if they're available in scope.

With this configuration, the blog post writer can now:
- Ask clarifying questions to the topic researcher if the research report is unclear
- Request additional information on specific topics
- Get help understanding complex concepts from the research

If you want the writer to be able to delegate to any agent in the crew, you can simply omit the `allowed_agents` parameter:

```python
@agent
def blog_post_writer(self) -> Agent:
  return Agent(
    config=self.agents_config['blog_post_writer'],
    verbose=True,
    tools=[ImageGenerationTool(base_path="./images")],
    allow_delegation=True  # Can delegate to any agent in the crew
  )
```

### What Happens Behind the Scenes

When you enable delegation for an agent, CrewAI automatically equips that agent with specialized delegation tools. These tools are added to the agent's toolset behind the scenes, without you needing to explicitly define or import them:

1. Ask Question Tool: This tool allows the agent to pose questions directly to another agent. When the blog writer uses this tool to ask the topic researcher a question, the researcher receives the question as a new task and responds with an answer. The response is then passed back to the writer, who can continue with its original task.

2. Delegate Work Tool: This tool enables an agent to assign a new task or subtask to another agent. This is more powerful than asking a question—it allows full task delegation where another agent takes over part of the work.

These tools are seamlessly integrated into the agent's workflow. When the blog post writer encounters something it needs clarification on, it can naturally decide to use the "Ask Question" tool, specifying the topic researcher as the recipient and the question it wants to ask. The CrewAI framework handles the routing, ensures the researcher receives the request, processes the response, and returns it to the writer—all transparently.

Here's how this might look in practice:
- The blog post writer starts writing a section about a technical concept from the research
- It realizes the research report doesn't provide enough detail on one specific aspect
- The writer uses the delegation tool to ask: "Can you provide more details on how [specific concept] works in the context of SEO?"
- The topic researcher receives this as a task, does additional research if needed, and responds
- The writer receives the answer and continues writing the blog post

This dynamic interaction makes crews more flexible and capable of handling complex scenarios where initial research might need refinement or clarification during the writing process.

### When to Use Delegation

Delegation is particularly useful when:
- Tasks have dependencies: Like our writer needing clarification from the researcher
- Work quality matters: When agents need to collaborate to produce the best output
- Information gaps emerge: When executing a task reveals missing information
- Expertise sharing: When one agent needs another agent's specialized knowledge

However, be mindful that delegation adds complexity and can increase execution time and token usage, as it introduces additional LLM calls for the delegated interactions. Use it judiciously where it provides real value to your workflow.

Whatever way you choose, running a crew works the same way. In your `main.py`, edit the `run` method as follows:

```python
def run():
    inputs = {
        'language': 'English',
        'country': 'US'
    }
    SeoCrew().crew().kickoff(inputs=inputs)
```

You can then run the crew using the `crewai` command:

```
crewai run
```

Because we set the `verbose` flag for all agents in our crew, we should see a live log of what's happening, and a few minutes later, we should get the notification that our crew finished its execution, and there should be a `blogpost.md` file with the newly written and illustrated blog post.