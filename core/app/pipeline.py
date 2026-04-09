class SentinelPipeline:
    def __init__(self, stages):
        self.stages = stages

    async def execute(self, ctx):
        for stage in self.stages:
            ctx = await stage.process(ctx)
            if ctx.errors: break # Останавливаемся, если что-то пошло не так
        return ctx
