## Release

### Development

#### Testing
```
PYTHONPATH=$(pwd)/src py.test -vvs tests
```

#### Coverage
```
PYTHONPATH=$(pwd)/src \
    py.test -vvs tests \
        --cov=setuptools_github.tools \
        --cov-report=html:build/coverage --cov-report=xml:build/coverage.xml \
        --junitxml=build/junit/junit.xml --html=build/junit/junit.html --self-contained-html
```

#### MyPy
```
PYTHONPATH=$(pwd)/src \
    mypy src \
        --no-incremental --xslt-html-report build/mypy
```


#### Betas
To test a beta/N.M.O branch:
```
make build
```


