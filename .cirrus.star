load("github.com/cirrus-modules/helpers", "task", "container", "script")


def main():
    images = [
        "python:3.8",
        "python:3.9",
        "python:3.10",
        "python:3.11",
    ]
    return [
        task(
            name="test",
            instance=container(img),
            instructions=[
                script("abc", "echo 'hi there1'"),
                script("def", "echo 'hi there2'"),
            ]
        )
        for img in images
    ]

