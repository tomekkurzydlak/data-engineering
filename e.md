

@router.post("/convert/batch/async", response_model=ConvertBatchAsyncCreateResponse, status_code=202)
async def convert_batch_async(request_body: ConvertBatchRequest, request: Request):
    app = request.app
    queue = app.state.conversion_queue
    settings = app.state.settings

    if not hasattr(app.state, "async_batches"):
        app.state.async_batches = {}

    batch_id = str(uuid4())
    submitted_at = _utc_now_iso()
    initial_results = [
        ConvertBatchItemResult(file_id=item.file_id, tenant_id=item.tenant_id, status="queued")
        for item in request_body.requests
    ]
    app.state.async_batches[batch_id] = {
        "batch_id": batch_id,
        "status": "queued",
        "submitted_at": submitted_at,
        "finished_at": None,
        "results": initial_results,
    }

    async def _run_batch():
        batch = app.state.async_batches.get(batch_id)
        if batch is None:
            return
        batch["status"] = "running"

        for idx, single_request in enumerate(request_body.requests):
            batch["results"][idx] = ConvertBatchItemResult(
                file_id=single_request.file_id,
                tenant_id=single_request.tenant_id,
                status="running",
            )
            try:
                result = await asyncio.wait_for(
                    queue.submit(single_request),
                    timeout=settings.conversion_timeout_seconds,
                )
                batch["results"][idx] = ConvertBatchItemResult(
                    file_id=single_request.file_id,
                    tenant_id=single_request.tenant_id,
                    status="success",
                    result=result,
                )
            except Exception as exc:  # noqa: BLE001
                batch["results"][idx] = ConvertBatchItemResult(
                    file_id=single_request.file_id,
                    tenant_id=single_request.tenant_id,
                    status="error",
                    error=str(exc),
                )

        batch["status"] = "completed"
        batch["finished_at"] = _utc_now_iso()

    asyncio.create_task(_run_batch())

    return ConvertBatchAsyncCreateResponse(
        batch_id=batch_id,
        status="queued",
        submitted_at=submitted_at,
        total=len(initial_results),
    )


@router.get("/convert/batch/async/{batch_id}", response_model=ConvertBatchAsyncStatusResponse)
async def get_convert_batch_async_status(batch_id: str, request: Request):
    app = request.app
    if not hasattr(app.state, "async_batches"):
        raise HTTPException(status_code=404, detail="Batch not found")

    batch = app.state.async_batches.get(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    results = batch["results"]
    succeeded = sum(1 for item in results if item.status == "success")
    failed = sum(1 for item in results if item.status == "error")
    in_progress = sum(1 for item in results if item.status == "running")
    queued = sum(1 for item in results if item.status == "queued")

    return ConvertBatchAsyncStatusResponse(
        batch_id=batch["batch_id"],
        status=batch["status"],
        submitted_at=batch["submitted_at"],
        finished_at=batch["finished_at"],
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        in_progress=in_progress,
        queued=queued,
        results=results,
    )
