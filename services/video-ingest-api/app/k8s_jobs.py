from __future__ import annotations

from kubernetes import client, config
from kubernetes.client import ApiException

from app.config import settings


def _batch_api() -> client.BatchV1Api:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.BatchV1Api()


def create_valorant_segment_job(job_id: str, source_path: str) -> str:
    """Create a k8s Job that runs the Valorant segmenter for one registered video."""
    batch = _batch_api()
    name = f"valorant-seg-{job_id[:8]}"
    body = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=settings.namespace,
            labels={
                "app.kubernetes.io/part-of": "homellm",
                "homellm.io/game": "valorant",
                "homellm.io/job-id": job_id,
            },
        ),
        spec=client.V1JobSpec(
            ttl_seconds_after_finished=600,
            backoff_limit=1,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={
                        "app": "valorant-segmenter",
                        "homellm.io/job-id": job_id,
                    }
                ),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name="segmenter",
                            image=settings.segmenter_image,
                            image_pull_policy="IfNotPresent",
                            env=[
                                client.V1EnvVar(name="JOB_ID", value=job_id),
                                client.V1EnvVar(name="SOURCE_PATH", value=source_path),
                                client.V1EnvVar(name="MEDIA_ROOT", value="/media"),
                                client.V1EnvVar(
                                    name="STUB_SEGMENT_SECONDS",
                                    value=str(settings.stub_segment_seconds),
                                ),
                            ],
                            volume_mounts=[
                                client.V1VolumeMount(name="media", mount_path="/media"),
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={"cpu": "250m", "memory": "256Mi"},
                                limits={"cpu": "1", "memory": "1Gi"},
                            ),
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="media",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name="video-media-pvc"
                            ),
                        )
                    ],
                ),
            ),
        ),
    )
    try:
        batch.create_namespaced_job(settings.namespace, body)
    except ApiException as exc:
        if exc.status != 409:
            raise
    return name


def create_valorant_analyzer_job(job_id: str) -> str:
    """Create a k8s Job that analyzes segmented rounds and sinks them back into the API."""
    batch = _batch_api()
    name = f"valorant-ana-{job_id[:8]}"
    body = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=name,
            namespace=settings.namespace,
            labels={
                "app.kubernetes.io/part-of": "homellm",
                "homellm.io/game": "valorant",
                "homellm.io/job-id": job_id,
            },
        ),
        spec=client.V1JobSpec(
            ttl_seconds_after_finished=600,
            backoff_limit=1,
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={
                        "app": "valorant-analyzer",
                        "homellm.io/job-id": job_id,
                    }
                ),
                spec=client.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        client.V1Container(
                            name="analyzer",
                            image=settings.analyzer_image,
                            image_pull_policy="IfNotPresent",
                            env=[
                                client.V1EnvVar(name="JOB_ID", value=job_id),
                                client.V1EnvVar(name="MEDIA_ROOT", value="/media"),
                                client.V1EnvVar(name="INTERNAL_API_BASE_URL", value=settings.internal_api_base_url),
                            ],
                            volume_mounts=[
                                client.V1VolumeMount(name="media", mount_path="/media"),
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={"cpu": "250m", "memory": "256Mi"},
                                limits={"cpu": "1", "memory": "1Gi"},
                            ),
                        )
                    ],
                    volumes=[
                        client.V1Volume(
                            name="media",
                            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                claim_name="video-media-pvc"
                            ),
                        )
                    ],
                ),
            ),
        ),
    )
    try:
        batch.create_namespaced_job(settings.namespace, body)
    except ApiException as exc:
        if exc.status != 409:
            raise
    return name
