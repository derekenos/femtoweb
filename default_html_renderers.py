
from lib._os import path


def HTMLDocument(head, body):
    return """
    <!DOCTYPE html>
    <html>

      <head>
        <meta charset="utf-8">
        {head}
      </head>

      <body>
        {body}
      </body>

    </html>
    """.format(head=head, body=body)


def Banner(text):
    return """
    <div id="banner">{text}</div>
    """.format(text=text)


def TextFileEditor(fs_path, text):
    filename = path.split(fs_path)[-1]
    head = """
    <script>
      document.addEventListener('DOMContentLoaded', () => {{
        const inputEl = document.getElementById('textarea')
        const buttonEl = document.getElementById('submit')

        function submit () {{
          fetch(new URL("/_fs{fs_path}", window.location.href), {{
            method: 'PUT',
            headers: {{
              'Content-Type': 'text/plain',
            }},
            redirect: 'follow',
            body: new File([inputEl.value], "{filename}")
          }})
          .then(response => {{
            if (response.redirected) {{
              window.location = response.url
            }}
          }})
          .catch(error => console.error('Error:', error));
        }}

        buttonEl.addEventListener('click', () => submit())

        inputEl.addEventListener('keydown', e => {{
          if (e.ctrlKey && e.key === "Enter") submit()
        }})
      }})
    </script>
    """.format(fs_path=fs_path, filename=filename)

    num_rows = text.count('\n') + 1
    body = """
    <textarea rows="{num_rows}" style="width: 100%;" id="textarea">{text}</textarea>
    <button id="submit">Submit</button>
    """.format(
        num_rows=num_rows,
        text=text
    )

    return HTMLDocument(head, body)
