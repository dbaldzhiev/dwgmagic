from dataclasses import dataclass

from jinja2 import Environment, DictLoader

from dwgmagic.core.context import ProjectConfig, ProjectContext
from dwgmagic.core.pipeline import PipelineRunner, PipelineStage
from dwgmagic.settings import Settings


@dataclass
class DummyStage(PipelineStage):
    name: str
    succeed: bool = True

    def run(self, context: ProjectContext):
        context.set(self.name, True)
        return context.environment.stage_result_factory(self.name, self.succeed)


class ResultFactoryEnvironment(Environment):
    def stage_result_factory(self, name, success):
        from dwgmagic.core.context import StageResult

        return StageResult(name=name, succeeded=success)


def make_context(tmp_path):
    settings = Settings(project_root=tmp_path)
    env = ResultFactoryEnvironment(loader=DictLoader({}))
    config = ProjectConfig(settings=settings)
    return ProjectContext(config=config, environment=env)


def test_pipeline_runner_short_circuits_on_failure(tmp_path):
    context = make_context(tmp_path)
    stages = [
        DummyStage("first"),
        DummyStage("second", succeed=False),
        DummyStage("third"),
    ]
    runner = PipelineRunner.from_iterable(stages)
    results = runner.run(context)
    assert [result.name for result in results] == ["first", "second"]
    assert results[-1].succeeded is False


def test_pipeline_runner_executes_all_on_success(tmp_path):
    context = make_context(tmp_path)
    stages = [DummyStage("first"), DummyStage("second"), DummyStage("third")]
    runner = PipelineRunner.from_iterable(stages)
    results = runner.run(context)
    assert [result.name for result in results] == ["first", "second", "third"]
    assert all(result.succeeded for result in results)
