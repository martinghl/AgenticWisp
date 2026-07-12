"""Claude 模型定价(每 1M token)与成本估算。纯数据,无副作用。"""

# (input_per_1M_usd, output_per_1M_usd)
PRICES = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-opus-4-5": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5": (10.0, 50.0),
    "claude-mythos-5": (10.0, 50.0),
}
DEFAULT = (5.0, 25.0)


def rate(model):
    """(input, output) per 1M;精确→前缀→default。"""
    if model in PRICES:
        return PRICES[model]
    for k, v in PRICES.items():
        if model and model.startswith(k):
            return v
    return DEFAULT


def cost(model, inp, out, cr, cc):
    """成本(美元):in·pi + out·po + cr·0.1·pi + cc·1.25·pi,按 1M 归一。
    cr=cache_read(便宜 0.1x),cc=cache_creation/写缓存(1.25x)。"""
    pi, po = rate(model)
    return (inp * pi + out * po + cr * pi * 0.1 + cc * pi * 1.25) / 1e6


# 各模型最大上下文窗口(token)
MAX_CONTEXT = {
    "claude-opus-4-8": 1_000_000, "claude-opus-4-7": 1_000_000,
    "claude-opus-4-6": 1_000_000, "claude-opus-4-5": 1_000_000,
    "claude-sonnet-5": 1_000_000, "claude-sonnet-4-6": 1_000_000,
    "claude-fable-5": 1_000_000, "claude-mythos-5": 1_000_000,
    "claude-haiku-4-5": 200_000,
}
DEFAULT_MAX_CONTEXT = 1_000_000


def max_context(model):
    """模型最大上下文窗口(token);精确→前缀→default。"""
    if model in MAX_CONTEXT:
        return MAX_CONTEXT[model]
    for k, v in MAX_CONTEXT.items():
        if model and model.startswith(k):
            return v
    return DEFAULT_MAX_CONTEXT
