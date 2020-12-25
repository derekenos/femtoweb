
from os import path

def HTMLDocument(body, head=''):
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

def _html_element(tag_name, self_closing=False):
    def f(inner_html, **kwargs):
        if self_closing and inner_html:
            raise AssertionError
        return '<{0} {1}>{2}{3}'.format(
            tag_name,
            ' '.join('{}="{}"'.format(k, v) for k, v in kwargs.items()),
            inner_html,
            '</{}>'.format(tag_name) if not self_closing else ''
        )
    return f

HTMLAnchorElement = _html_element('a')
HTMLSpanElement = _html_element('span')

def Banner(text):
    return """
    <div id="banner">{text}</div>
    """.format(text=text)

def TextFileEditor(req_path, text):
    filename = path.split(req_path)[-1]
    head = """
    <script>
      document.addEventListener('DOMContentLoaded', () => {{
        const inputEl = document.getElementById('textarea')
        const buttonEl = document.getElementById('submit')

        function submit () {{
          fetch(new URL("/_fs/{req_path}", window.location.href), {{
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
    """.format(req_path=req_path, filename=filename)

    num_rows = text.count('\n') + 1
    body = """
    <textarea rows="{num_rows}" style="width: 100%;" id="textarea">{text}</textarea>
    <button id="submit">Submit</button>
    """.format(
        num_rows=num_rows,
        text=text
    )

    return HTMLDocument(body, head)
