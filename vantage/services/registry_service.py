from vantage.core.logging import get_logger
from vantage.domain.experiments import Experiment, ExperimentResult, ExperimentStatus
from vantage.storage.base import AbstractMetadataRepository

logger = get_logger(__name__)


class RegistryService:
    """Service managing the Experiment Registry lifecycle."""

    def __init__(self, metadata_repo: AbstractMetadataRepository):
        self._repo = metadata_repo

    async def get_experiment(self, experiment_id: str) -> Experiment | None:
        return await self._repo.get_experiment(experiment_id)

    async def save_experiment(self, experiment: Experiment) -> Experiment:
        saved = await self._repo.save_experiment(experiment)
        logger.info("experiment_saved", experiment_id=saved.id, slug=saved.slug)
        return saved

    async def list_experiments(
        self, project_id: str | None = None, status: str | None = None
    ) -> list[Experiment]:
        return await self._repo.list_experiments(project_id=project_id, status=status)

    async def update_status(self, experiment_id: str, new_status: ExperimentStatus) -> Experiment | None:
        exp = await self._repo.get_experiment(experiment_id)
        if not exp:
            return None
        updated = exp.model_copy(update={"status": new_status})
        return await self._repo.save_experiment(updated)

    async def record_result(self, experiment_id: str, result: ExperimentResult) -> Experiment | None:
        exp = await self._repo.get_experiment(experiment_id)
        if not exp:
            return None
        updated = exp.model_copy(
            update={"result": result, "status": ExperimentStatus.COMPLETED}
        )
        return await self._repo.save_experiment(updated)
