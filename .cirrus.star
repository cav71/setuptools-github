load("github.com/cirrus-modules/helpers", "task", "container", "script")


def main():
    images = [
        "python:3.8",
        "python:3.9",
        "python:3.10",
        "python:3.11",
    ]
    containers = [
        container,
        windows_container,
        macos_instance,
    ]

    tasks = []
    for cont in containers:
        for img in images:
            tasks.append(task(
                name="test",
                instance=container(img),
                instructions=[
                    script("abc", "echo 'hi there1'"),
                    script("def", "echo 'hi there2'"),
                ]
            ))
    return tasks

