from __future__ import annotations

import argparse
import json
from pathlib import Path

from medsiglab import config, reporting


def build_report_body(metrics: dict) -> str:
    p1e1 = metrics["part1"]["exp1"]
    p1e2 = metrics["part1"]["exp2"]
    p1e3 = metrics["part1"]["exp3"]
    p1e4 = metrics["part1"]["exp4"]
    p2e1 = metrics["part2"]["exp1"]
    p2e2 = metrics["part2"]["exp2"]
    p2e3 = metrics["part2"]["exp3"]

    orders = p1e1["orders"]
    p1e1_rows = {row["滤波器"]: row for row in p1e1["rows"]}
    cutoff_rows = {row["条件"]: row for row in p1e4["cutoff_rows"]}
    order_rows = {row["条件"]: row for row in p1e4["order_rows"]}
    exp2_rows = {row["方式"]: row for row in p1e2["rows"]}
    p2_method_rows = {row["方法"]: row for row in p2e1["rows"]}
    p1e3_drift = {row["Block"]: row for row in p1e3["drift_rows"]}
    p1e3_syn = {row["截止频率/Hz"]: row for row in p1e3["synthetic_rows"]}
    p2_window_rows = {row["窗函数"]: row for row in p2e2["window_rows"]}
    p2_length_rows = {row["taps"]: row for row in p2e2["length_rows"]}

    text = ""
    text += reporting.paragraph(r"\section{实验设置与数据说明}")
    text += reporting.paragraph(
        "本报告围绕医学信号滤波实验中的 IIR 与 FIR 两部分内容展开。"
        "数据处理、滤波器设计、统计指标计算和图表绘制均采用 Python 完成，报告正文按照实验过程、结果和讨论的顺序组织。"
    )
    text += reporting.paragraph(
        f"真实 ERP 数据源为 \\texttt{{sub7A.mat}}，其原始采样率通过触发间隔与配套例程可核实为 {metrics['data']['original_fs']:.0f} Hz。"
        "但本文仍严格按题面口径完成真实数据实验：Part-I 相关 ERP 实验先重采样至 200 Hz，Part-II 实验三先重采样至 1000 Hz。"
        "所有真实 ERP 分析均使用两块连续数据中的目标试次，先按 Block 分别滤波和分段，再合并叠加平均。"
    )
    text += reporting.paragraph(
        f"统一 ERP 预处理参数如下：时间窗 {config.EPOCH_TMIN * 1000:.0f} ms 到 {config.EPOCH_TMAX * 1000:.0f} ms，"
        f"基线区间 {config.BASELINE[0] * 1000:.0f} ms 到 {config.BASELINE[1] * 1000:.0f} ms，重参考电极为 TP7/TP8，"
        "主观察导联为 Fz。触发点按配套例程的索引语义直接使用，不做额外的 $-1$ 校正。"
    )
    text += reporting.paragraph(r"\subsection*{数据概览}")
    text += reporting.paragraph(rf"\input{{output/tables/data-summary.tex}}")

    text += reporting.paragraph(r"\section{Part-I IIR 滤波器设计、实现与失真评估}")
    text += reporting.paragraph(r"\subsection{实验一：统一指标下的四类 IIR 低通滤波器设计}")
    text += reporting.paragraph(r"\subsubsection*{实验方法}")
    text += reporting.paragraph(
        "设计指标为：$f_s=1000$ Hz，通带边缘 40 Hz，阻带边缘 60 Hz，通带最大波纹 1 dB，阻带最小衰减 40 dB。"
        "采用 Butterworth、Chebyshev-I、Chebyshev-II 与 Elliptic 四类 IIR 低通，并用阶数估计函数确定最低满足阶数。"
    )
    text += reporting.paragraph(
        "对每一类滤波器，先依据同一组通带和阻带指标求得最低满足阶数，再计算其复频率响应。"
        "在统一频率网格上提取通带波纹、阻带最小衰减、过渡带宽度以及通带内群时延的均值与标准差。"
        "这样可以在“是否满足幅度规格”之外，进一步比较不同设计在相位和时域解释上的代价。"
    )
    text += reporting.figure_block("四类 IIR 低通滤波器的幅频、相频与群时延比较。", p1e1["figure"])
    text += reporting.paragraph(rf"\input{{{p1e1['table']}}}")
    text += reporting.paragraph(r"\subsubsection*{分析与讨论}")
    text += reporting.paragraph(
        f"图 1 和表格表明，四类 IIR 低通都满足题设的 40/60 Hz 幅度指标，但实现代价和时域代价明显不同。"
        f"Butterworth 需要 {orders['Butterworth']} 阶，Chebyshev-I 与 Chebyshev-II 均为 {orders['Chebyshev-II']} 阶，Elliptic 仅需 {orders['Elliptic']} 阶。"
        f"其中 Elliptic 的过渡带最窄，仅约 {p1e1_rows['Elliptic']['过渡带宽/Hz']:.2f} Hz；Butterworth 的过渡带约为 {p1e1_rows['Butterworth']['过渡带宽/Hz']:.2f} Hz，说明其幅频滚降相对平缓。"
    )
    text += reporting.paragraph(
        f"从群时延看，Butterworth 在通带内的平均群时延约为 {p1e1_rows['Butterworth']['通带群时延均值/ms']:.2f} ms，"
        f"标准差约为 {p1e1_rows['Butterworth']['通带群时延标准差/ms']:.2f} ms；Chebyshev-II 的平均群时延较小，约为 {p1e1_rows['Chebyshev-II']['通带群时延均值/ms']:.2f} ms，"
        f"但 Elliptic 和 Chebyshev-I 的群时延波动更明显。由此可见，频率选择性更强并不意味着时域保真更好，通带群时延的起伏同样会影响生物医学信号的峰位解释。"
    )
    text += reporting.paragraph(
        "这一实验说明，在滤波器选型时不能只以“最低阶数”或“最陡滚降”作为唯一标准。"
        "对于需要解读峰潜伏期和波形细节的医学信号，幅频响应、相频响应和群时延应当同时纳入判断；"
        "否则，即使滤波器在频域上达标，也可能在时域中引入不容易察觉却会影响解释的形态偏差。"
    )
    text += reporting.qa_block(
        "实验一思考题回答",
        [
            (
                "为什么在相同严苛指标下，不同滤波器所需的阶数差异巨大？",
                f"因为四类 IIR 在“平坦性、等波纹分配和过渡带压缩方式”上的优化目标不同。本实验中 Butterworth 需要 {orders['Butterworth']} 阶，"
                f"Chebyshev-I 需要 {orders['Chebyshev-I']} 阶，Chebyshev-II 需要 {orders['Chebyshev-II']} 阶，Elliptic 仅需 {orders['Elliptic']} 阶。"
                f"结合图 1 可以看到，Elliptic 在只用 {orders['Elliptic']} 阶的情况下就把过渡带压缩到约 {p1e1_rows['Elliptic']['过渡带宽/Hz']:.2f} Hz，"
                "说明一旦允许波纹存在，有限阶数就可以更集中地用于压缩过渡带，因此阶数会明显下降。"
            ),
            (
                "哪一类滤波器更强调通带平坦，哪一类更强调过渡带陡峭？",
                f"Butterworth 最强调通带平坦，因此通带最光滑但通常阶数最高；本实验中它需要 {orders['Butterworth']} 阶。"
                f"Elliptic 同时允许通带和阻带等波纹，所以在相同指标下过渡带最陡，其过渡带宽仅约 {p1e1_rows['Elliptic']['过渡带宽/Hz']:.2f} Hz。"
                "Chebyshev-I 主要牺牲通带平坦换取陡峭，Chebyshev-II 则主要在阻带引入等波纹。"
            ),
            (
                "为什么 IIR 滤波器的相位通常不是线性的？",
                "因为 IIR 由极点和零点的有理函数决定，其相位响应随频率变化并不满足线性相位的对称条件。"
                "从图 1 的相频和群时延子图可以看到，四类 IIR 在通带内都存在明显的非恒定延迟，因此不同频率分量会经历不同推迟，波形形态会被重塑，而不是简单平移。"
            ),
            (
                "为什么在生物医学信号处理中，群时延比单纯的相频响应更值得关注？",
                f"群时延直接描述局部包络和峰位被推迟了多少时间，对 ERP 峰潜伏期解释更敏感。"
                f"例如本实验中 Butterworth 的通带群时延均值约为 {p1e1_rows['Butterworth']['通带群时延均值/ms']:.2f} ms，而 Chebyshev-II 约为 {p1e1_rows['Chebyshev-II']['通带群时延均值/ms']:.2f} ms；"
                "相频曲线虽然也显示非线性，但不如群时延直观，因此后者更适合直接评估滤波后峰位是否会被改写。"
            ),
        ],
    )

    text += reporting.paragraph(r"\subsection{实验二：低通滤波器的滤波效果、相位失真与重复滤波}")
    text += reporting.paragraph(r"\subsubsection*{实验方法}")
    text += reporting.paragraph(
        "人工信号为 $x(t)=\sin(2\pi 10 t)+\sin(2\pi 50 t)$，使用 4 阶 Butterworth 20 Hz 低通分别进行单次因果滤波、两次串联因果滤波和零相位滤波。"
        "时间偏移通过与理想 10 Hz 分量在中心时间段互相关估计。频谱采用一侧幅度谱，并按 $2|X(f)|/N$ 归一化。"
    )
    text += reporting.paragraph(
        "该实验以可控人工信号代替真实生理数据，目的是把“频率选择性”和“相位失真”分开观察。"
        "其中 10 Hz 分量代表需要保留的低频有效成分，50 Hz 分量代表需要抑制的高频干扰。"
        "通过比较三种处理方案在幅频、延迟和边界处波形上的差异，可以直接观察因果滤波、重复滤波和零相位滤波各自的代价。"
    )
    text += reporting.figure_block("单次因果、重复因果与零相位低通处理的时域、频域与边界效应比较。", p1e2["figure"])
    text += reporting.paragraph(rf"\input{{{p1e2['table']}}}")
    text += reporting.paragraph(r"\subsubsection*{分析与讨论}")
    text += reporting.paragraph(
        f"图 2 表明三种处理方式都能显著压制 50 Hz 成分，但代价并不相同。"
        f"单次因果滤波把 50 Hz 分量压到 {exp2_rows['Single causal']['50 Hz幅值']:.4f}，抑制量约为 {abs(exp2_rows['Single causal']['50 Hz抑制/dB']):.2f} dB；"
        f"重复因果滤波进一步压低到 {exp2_rows['Repeated causal']['50 Hz幅值']:.4f}，抑制量约为 {abs(exp2_rows['Repeated causal']['50 Hz抑制/dB']):.2f} dB；"
        f"零相位滤波则在保留 10 Hz 主成分幅值 {exp2_rows['Zero phase']['10 Hz幅值']:.3f} 的同时，将 50 Hz 分量压制到 {exp2_rows['Zero phase']['50 Hz幅值']:.4f}。"
    )
    text += reporting.paragraph(
        f"更关键的差别出现在时域。单次因果滤波的延迟约为 {p1e2['delay_single_ms']:.2f} ms，重复因果滤波增大到 {p1e2['delay_twice_ms']:.2f} ms，"
        f"零相位滤波则接近 {p1e2['delay_zero_ms']:.2f} ms。图 2 的边界局部放大还显示，零相位滤波虽然避免了整体相位偏移，但在记录起止位置会出现更明显的边界处理痕迹，因此它适合离线分析而不适合实时系统。"
    )
    text += reporting.paragraph(
        "从方法学上看，这一实验给出的不是“哪一种滤波总是最好”的结论，而是“不同场景下优先级不同”。"
        "如果目标是尽量保持峰位和波形结构，零相位处理最有优势；"
        "如果目标是在线处理或实时监测，则必须接受因果实现带来的延迟和形态改写。"
        "重复因果滤波虽然能进一步提高抑制量，但其带来的时域畸变也同步累积，因此不能简单地把“多滤一次”视为无代价优化。"
    )
    text += reporting.qa_block(
        "实验二思考题回答",
        [
            (
                "为什么单次因果滤波后的波形会出现明显的时间偏移？",
                f"因为因果 IIR 在 10 Hz 附近具有正群时延，本实验中单次因果滤波相对理想 10 Hz 波形的估计延迟约为 {p1e2['delay_single_ms']:.2f} ms。"
                "图 2 的时域波形已经可以看到主振荡整体后移，它不是整体平移所有频率，而是对不同频率施加不同延迟，因此复合波形会发生相位失真。"
            ),
            (
                "为什么重复因果滤波会进一步恶化波形畸变？",
                f"重复因果滤波会把相位延迟和幅度整形叠加两次，本实验中重复因果滤波的估计延迟扩大到 {p1e2['delay_twice_ms']:.2f} ms，"
                f"同时 50 Hz 抑制增强到约 {abs(exp2_rows['Repeated causal']['50 Hz抑制/dB']):.2f} dB。也就是说，它在进一步清除高频成分的同时，把时域失真一并放大了。"
            ),
            (
                "零相位滤波（filtfilt）为什么能解决相位失真？",
                f"前向-后向滤波会让前向相位延迟被后向过程抵消，因此净相位几乎为零。本实验中零相位处理的估计延迟约为 {p1e2['delay_zero_ms']:.2f} ms，"
                f"同时 10 Hz 主成分幅值仍为 {exp2_rows['Zero phase']['10 Hz幅值']:.3f}，说明峰位基本回到理想位置且主要有效成分得到保留。"
            ),
            (
                "零相位滤波本质上是非因果的，它是否适用于所有生物医学信号处理场景？为什么？",
                "不适用于所有场景。它非常适合离线 ERP、ECG 或 EEG 后处理，因为可以最大限度保持峰位；"
                "但图 2 的边界放大已经提示它依赖前后双向数据，在实时监测、闭环刺激、床旁报警和植入式设备中，未来样本不可用，零相位滤波就无法实施。"
            ),
        ],
    )

    text += reporting.paragraph(r"\subsection{实验三：高通滤波器、慢漂移与时间常数}")
    text += reporting.paragraph(r"\subsubsection*{实验方法}")
    text += reporting.paragraph(
        "真实数据部分先把连续 ERP 重采样到 200 Hz，然后观察 Fz 原始波形和 1 Hz 高通零相位滤波后的变化。"
        "人工信号部分固定 4 阶 Butterworth 高通，只改变截止频率 0.1、0.5 和 1.0 Hz。"
    )
    text += reporting.paragraph(
        "真实数据分析中，先对两个连续 Block 分别重采样，再提取 Fz 导联连续波形，比较滤波前后的慢漂移范围。"
        "为了突出低频趋势，另外对连续波形做 5 s 窗长的滑动平均，并用其峰峰值量化慢变范围。"
        "人工信号则由 0.2 Hz 正弦漂移与位于 1.5 s 的高斯脉冲叠加而成，从而在已知真值的条件下观察高通截止频率对峰值、恢复过程和后冲的影响。"
    )
    text += reporting.figure_block("连续 Fz 波形中的慢漂移，以及 1 Hz 高通后漂移被显著压缩。", p1e3["figure_continuous"])
    text += reporting.paragraph(rf"\input{{{p1e3['table_continuous']}}}")
    text += reporting.figure_block("人工漂移+脉冲信号在不同高通截止频率下的基线恢复与形态失真。", p1e3["figure_synthetic"])
    text += reporting.paragraph(rf"\input{{{p1e3['table_synthetic']}}}")
    text += reporting.paragraph(r"\subsubsection*{分析与讨论}")
    text += reporting.paragraph(
        f"真实连续数据中，1 Hz 高通对慢漂移的抑制非常明显。Block 1 的慢变范围由 {p1e3_drift['Block 1']['原始慢变范围/uV']:.2f} uV 降到 {p1e3_drift['Block 1']['高通后慢变范围/uV']:.2f} uV，"
        f"Block 2 则由 {p1e3_drift['Block 2']['原始慢变范围/uV']:.2f} uV 降到 {p1e3_drift['Block 2']['高通后慢变范围/uV']:.2f} uV。"
        "图 3 上半部分可以直接看到基线摆动被明显压平，说明高通滤波对低频漂移非常敏感。"
    )
    text += reporting.paragraph(
        f"人工信号进一步说明，随着高通截止频率从 0.1 Hz 提高到 1.0 Hz，脉冲峰值从 {p1e3_syn[0.1]['脉冲峰值/uV']:.2f} uV 降到 {p1e3_syn[1.0]['脉冲峰值/uV']:.2f} uV，"
        f"后冲最小值则从 {p1e3_syn[0.1]['后冲最小值/uV']:.3f} uV 变为 {p1e3_syn[1.0]['后冲最小值/uV']:.3f} uV。"
        "这说明基线恢复虽然更快，但慢变化有效成分也被一并压缩，波形后段甚至会出现额外负偏转。"
    )
    text += reporting.paragraph(
        "因此，高通滤波在 ERP 分析中的意义不只是“去漂移”，更是对低频信息的重新分配。"
        "如果只根据视觉上基线是否平稳来判断滤波效果，很容易忽略对慢波成分的破坏。"
        "对单个 epoch 而言，慢漂移会改变刺激前基线段的均值，使基线校正后仍残留偏移；对多试次平均而言，不同试次的基线偏移和缓慢趋势会增大试次间方差，污染晚期慢波并降低叠加平均后的可解释性。"
        "本实验通过真实数据和人工信号两条证据链同时说明：较高的高通截止频率确实能改善基线稳定性，但这种改善往往是以牺牲时域保真和平均稳定性为代价换来的。"
    )
    text += reporting.qa_block(
        "实验三思考题回答",
        [
            (
                "高通滤波器为什么不只是简单地“去掉直流分量”？",
                "高通滤波器抑制的是一整段低频成分，而不是单独一个 0 Hz 点。"
                "图 3 下半部分中，截止频率升高后不仅基线回到零点附近，脉冲后的恢复过程和后冲形态也一起变化，说明 ERP 的慢波、基线漂移和长时程恢复过程都会被同时改写。"
            ),
            (
                "为什么高通截止频率越高，基线恢复越快，但慢变化的有效成分也越容易被削弱？",
                f"因为截止频率升高意味着更多接近直流的慢成分被当成“噪声”压制。人工信号结果显示，截止频率从 0.1 Hz 提高到 1.0 Hz 后，脉冲峰值由 {p1e3_syn[0.1]['脉冲峰值/uV']:.2f} uV 降到 {p1e3_syn[1.0]['脉冲峰值/uV']:.2f} uV，"
                f"后冲最小值由 {p1e3_syn[0.1]['后冲最小值/uV']:.3f} uV 变为 {p1e3_syn[1.0]['后冲最小值/uV']:.3f} uV，说明恢复更快的同时，慢变化有效成分也被削弱。"
            ),
            (
                "在 ERP 研究中，去漂移与保留慢波成分之间存在什么不可调和的矛盾？",
                f"去漂移要求较高高通截止频率，以便快速恢复基线；保留晚期慢波则要求截止频率尽可能低。"
                f"本实验里 1 Hz 高通确实把 Block 1 的慢变范围压到 {p1e3_drift['Block 1']['高通后慢变范围/uV']:.2f} uV，但人工脉冲的峰值和后段形态也随之改变。"
                "同时，试次间漂移还会放大平均前的方差并污染基线校正结果，这说明两者共享同一低频频段，无法同时最优，只能在稳定基线和形态保真之间折中。"
            ),
        ],
    )

    text += reporting.paragraph(r"\subsection{实验四：ERP 信号分析中滤波器选择对结果的影响}")
    text += reporting.paragraph(r"\subsubsection*{实验方法}")
    text += reporting.paragraph(
        "真实 ERP 主分析严格使用两块数据中的全部目标试次，先分块滤波和分段，再合并叠加平均。"
        "本实验中高通截止频率比较采用零相位 Butterworth 方案，滚降速度比较采用因果 Butterworth 方案。"
    )
    text += reporting.paragraph(
        "在截止频率比较部分，分别构造 50 Hz 低通、0.1--15 Hz、0.5--15 Hz 和 1.0--15 Hz 四种条件。"
        "对每种条件均采用相同的分段窗口、基线校正和双乳突重参考，并在平均 ERP 上提取 250--650 ms 区间内的晚期正峰、0--250 ms 区间的早期最小值以及 300--700 ms 面积。"
        "在滚降速度比较部分，则固定低通 15 Hz、高通 2.5 Hz，只改变高通阶数为 2 阶与 8 阶，并使用因果实现，以便观察更陡滚降在时域上是否引入更明显的过冲、振荡和峰位偏移。"
    )
    text += reporting.figure_block("不同高通截止频率下 Fz 平均 ERP 的对比。", p1e4["figure_cutoff"])
    text += reporting.paragraph(rf"\input{{{p1e4['table_cutoff']}}}")
    text += reporting.figure_block("相同截止频率但不同高通阶数的因果滤波结果，高阶条件带来更明显的时域伪迹与峰位后移。", p1e4["figure_order"])
    text += reporting.paragraph(rf"\input{{{p1e4['table_order']}}}")
    text += reporting.paragraph(r"\subsubsection*{分析与讨论}")
    text += reporting.paragraph(
        f"不同高通截止频率的比较表明，截止频率过高会直接改写晚期 ERP 成分。"
        f"0.1--15 Hz 条件下 Pe 峰值约为 {cutoff_rows['0.1-15 Hz']['Pe峰值/uV']:.2f} uV，300--700 ms 面积约为 {cutoff_rows['0.1-15 Hz']['300-700 ms面积']:.3f}；"
        f"当高通提高到 1.0--15 Hz 时，Pe 峰值下降到 {cutoff_rows['1.0-15 Hz']['Pe峰值/uV']:.2f} uV，面积缩小到 {cutoff_rows['1.0-15 Hz']['300-700 ms面积']:.3f}。"
        "图 5 中晚期正波明显被压窄，且早期负向分量被放大。"
    )
    text += reporting.paragraph(
        f"阶数比较说明，即使截止频率相同，时域形态也会随着滚降速度改变。"
        f"2 阶高通条件下正峰约为 {order_rows['2nd-order HP']['正峰/uV']:.2f} uV，潜伏期约 {order_rows['2nd-order HP']['正峰潜伏期/ms']:.0f} ms；"
        f"8 阶条件下正峰降到 {order_rows['8th-order HP']['正峰/uV']:.2f} uV，潜伏期后移到 {order_rows['8th-order HP']['正峰潜伏期/ms']:.0f} ms。"
        f"从早期时域伪迹指标看，8 阶条件在 0--250 ms 内相对 50 Hz 低通参考的差异 RMS 为 {order_rows['8th-order HP']['0-250 ms差异RMS/uV']:.3f} uV，"
        f"明显高于 2 阶条件的 {order_rows['2nd-order HP']['0-250 ms差异RMS/uV']:.3f} uV；其早期正过冲也达到 {order_rows['8th-order HP']['早期正过冲/uV']:.3f} uV，高于 2 阶条件的 {order_rows['2nd-order HP']['早期正过冲/uV']:.3f} uV。"
        "结合图 6 可见，更高阶的因果高通不一定在单一负向极值上更深，但会造成更明显的峰位后移和更不均匀的早期时域畸变。"
    )
    text += reporting.paragraph(
        "这一部分最重要的方法学结论是：ERP 滤波参数本身会进入科学结论。"
        "如果参数设置过强，滤波器不再只是“改善信噪比”的预处理步骤，而是会改变晚期成分的幅值、面积甚至潜伏期。"
        "因此，报告中不仅需要给出结果图，更应明确写出截止频率、阶数、因果性以及评价指标，否则他人无法判断结论究竟来自数据本身还是来自滤波设置。"
    )
    text += reporting.qa_block(
        "实验四思考题回答",
        [
            (
                "为什么将高通截止频率从 0.1 Hz 提高到 1 Hz，会对 ERP 晚期成分产生灾难性的形态破坏？",
                f"因为晚期 Pe 本身就是低频、宽时程成分。表格显示 0.1--15 Hz 与 1.0--15 Hz 条件下，Pe 峰值由 {cutoff_rows['0.1-15 Hz']['Pe峰值/uV']:.2f} uV 降到 {cutoff_rows['1.0-15 Hz']['Pe峰值/uV']:.2f} uV，"
                f"300--700 ms 面积也由 {cutoff_rows['0.1-15 Hz']['300-700 ms面积']:.3f} 缩小到 {cutoff_rows['1.0-15 Hz']['300-700 ms面积']:.3f}，说明较高高通把真正的晚期成分一并削掉了。"
            ),
            (
                "为什么“更平滑干净的基线”并不一定意味着提取到了“更真实的 ERP”？",
                "因为干净的基线可能来自对低频脑成分的过度压制。图 5 中 1.0--15 Hz 的基线确实更平整，但晚期正波幅值和面积都明显下降；"
                "如果滤掉的恰好包含真实生理慢波，那么“平滑”反而是失真的证据。"
            ),
            (
                "为什么在截止频率相同的情况下，仅仅增加阶数会改变 ERP 的形态？",
                f"因为更高阶数对应更长、更强振荡的冲激响应。这里 2.5 Hz 高通从 2 阶升到 8 阶后，正峰由 {order_rows['2nd-order HP']['正峰/uV']:.2f} uV 降到 {order_rows['8th-order HP']['正峰/uV']:.2f} uV，"
                f"潜伏期也由 {order_rows['2nd-order HP']['正峰潜伏期/ms']:.0f} ms 后移到 {order_rows['8th-order HP']['正峰潜伏期/ms']:.0f} ms；"
                f"同时 0--250 ms 内相对参考波形的差异 RMS 由 {order_rows['2nd-order HP']['0-250 ms差异RMS/uV']:.3f} uV 增至 {order_rows['8th-order HP']['0-250 ms差异RMS/uV']:.3f} uV。"
                "这说明阶数增加不仅改变幅度选择性，也会通过更长的冲激响应带来更明显的时域畸变和峰位偏移。"
            ),
            (
                "为什么在生物医学信号处理中，“极窄的过渡带”与“时域形态保真”往往不能同时满足？",
                "因为极窄过渡带通常意味着更长或更强振荡的冲激响应。"
                "图 6 中更高阶的因果高通虽然滚降更陡，但波形同时出现更明显的峰位后移和更大的早期差异 RMS；ERP 这种依赖形态和潜伏期解释的信号，对这种时域代价尤其敏感。"
            ),
        ],
    )

    text += reporting.paragraph(r"\section{Part-II FIR 滤波器设计与应用}")
    text += reporting.paragraph(r"\subsection{实验一：三种 FIR 设计方法比较}")
    text += reporting.paragraph(r"\subsubsection*{实验方法}")
    text += reporting.paragraph(
        "在 1000 Hz 采样率下，分别用海明窗窗函数法、频域采样法和等波纹逼近法设计满足 40/60 Hz 规格的 FIR 低通，并比较达到指标时所需的最短奇数 taps。"
    )
    text += reporting.paragraph(
        "三种方法均以同一组幅度指标为约束：通带边缘 40 Hz、阻带边缘 60 Hz、通带最大波纹 1 dB、阻带最小衰减 50 dB。"
        "对每一类设计方法都从较小的奇数 taps 开始搜索，直到实际频率响应满足上述指标为止，再记录其最短长度、固定群时延和实际波纹/衰减。"
        "这种处理方式保证比较对象具有相同设计目标，从而使“长度差异”本身具有解释意义。"
    )
    text += reporting.figure_block("三种 FIR 低通设计方法的幅频、相频和群时延比较。", p2e1["figure"])
    text += reporting.paragraph(rf"\input{{{p2e1['table']}}}")
    text += reporting.paragraph(r"\subsubsection*{分析与讨论}")
    text += reporting.paragraph(
        f"三种 FIR 设计方法都能满足题设幅度指标，但长度差异非常明显。"
        f"等波纹法仅需 {p2_method_rows['Equiripple']['最短taps']:.0f} taps，对应固定群时延 {p2_method_rows['Equiripple']['固定群时延/ms']:.0f} ms；"
        f"海明窗法需要 {p2_method_rows['Window-Hamming']['最短taps']:.0f} taps，固定群时延 {p2_method_rows['Window-Hamming']['固定群时延/ms']:.0f} ms；"
        f"频域采样法则达到 {p2_method_rows['Frequency Sampling']['最短taps']:.0f} taps，固定群时延长达 {p2_method_rows['Frequency Sampling']['固定群时延/ms']:.0f} ms。"
    )
    text += reporting.paragraph(
        f"从表格可以看出，等波纹法的通带波纹约为 {p2_method_rows['Equiripple']['通带波纹/dB']:.3f} dB，已经接近 1 dB 设计上限，"
        f"说明它更充分地利用了允许误差；海明窗法的通带波纹只有 {p2_method_rows['Window-Hamming']['通带波纹/dB']:.3f} dB，阻带衰减约为 {p2_method_rows['Window-Hamming']['阻带衰减/dB']:.2f} dB，"
        "幅度性能同样合格，但并没有像等波纹法那样把误差集中压缩到最经济的长度。"
    )
    text += reporting.paragraph(
        f"图 7 中频域采样法在阻带起始处出现的黄色“密集堆叠”现象并不是绘图错误，而是超长 FIR 在高分辨率频响图中的正常视觉表现。"
        f"本实验中该方法为了满足同样的 40/60 Hz 指标，长度达到 {p2_method_rows['Frequency Sampling']['最短taps']:.0f} taps，远高于另外两种方法。"
        "如此长的线性相位 FIR 会在阻带内形成非常密集的零点和纹波起伏，缩小后就会表现为一片较厚的色带。"
        "因此，这个现象本身也从侧面说明：频域采样法虽然能够达标，但其代价是极长的滤波器长度和极大的固定群时延。"
    )
    text += reporting.paragraph(
        "这一结果说明，FIR 设计方法的差别不只体现在“是否线性相位”，更体现在误差分配策略。"
        "等波纹法通过最小化最大误差，把有限长度的自由度尽可能用于满足指标边界；"
        "窗函数法则保留了实现简单、行为稳定的优点，但在严格指标下往往需要更长滤波器。"
        "如果研究场景对固定延迟十分敏感，那么方法选择本身就会成为工程可行性的关键。"
    )
    text += reporting.qa_block(
        "实验一思考题回答",
        [
            (
                "为什么在相同指标下，不同 FIR 设计方法达到要求所需的滤波器长度会明显不同？",
                f"因为三种方法分配逼近误差的策略不同。实验结果中海明窗法需要 {p2_method_rows['Window-Hamming']['最短taps']:.0f} taps，"
                f"频域采样法需要 {p2_method_rows['Frequency Sampling']['最短taps']:.0f} taps，等波纹法需要 {p2_method_rows['Equiripple']['最短taps']:.0f} taps。"
                f"图 7 已经显示出频域采样法的群时延远高于另外两种方法，说明允许在整个频带内重新分配误差的方法，会更节省长度。"
            ),
            (
                "为什么等波纹逼近法通常能在较短长度下达到较好的幅度逼近性能？",
                f"因为等波纹法按 minimax 准则压缩最大误差，把可容忍误差在通带与阻带内“均匀用满”。本实验中它在 {p2_method_rows['Equiripple']['最短taps']:.0f} taps 下就达到约 {p2_method_rows['Equiripple']['阻带衰减/dB']:.2f} dB 的阻带衰减，"
                "因此同等规格下通常最省 taps。"
            ),
            (
                "频域采样法的思想非常直观，但为什么它在严格工程指标下往往不一定最经济？",
                f"因为它对有限频率采样点的逼近更直接，但并不显式最小化全频带最大误差；本实验中为了把过渡带和阻带都压到要求，频域采样法需要 {p2_method_rows['Frequency Sampling']['最短taps']:.0f} taps，"
                f"其固定群时延达到 {p2_method_rows['Frequency Sampling']['固定群时延/ms']:.0f} ms，远高于另外两种方法。"
            ),
            (
                "对于线性相位 FIR 滤波器而言，群时延虽然恒定，但为什么它仍然可能成为实际应用中的严重负担？",
                f"因为恒定并不等于很小。图 7 的群时延子图显示，等波纹法虽然最短，固定延迟仍有 {p2_method_rows['Equiripple']['固定群时延/ms']:.0f} ms；"
                f"频域采样法更是达到 {p2_method_rows['Frequency Sampling']['固定群时延/ms']:.0f} ms。"
                "一旦 taps 很长，整体延迟会达到数十甚至数百毫秒，对实时监测和闭环控制都是明显负担。"
            ),
        ],
    )

    text += reporting.paragraph(r"\subsection{实验二：窗函数与滤波器长度对 FIR 性能的影响}")
    text += reporting.paragraph(r"\subsubsection*{实验方法}")
    text += reporting.paragraph(
        "本实验分为两组比较。第一组固定 61 taps，分别选用 Bartlett、Hann、Hamming 和 Blackman 窗构造低通 FIR，以观察不同窗口形状如何改变过渡带和阻带泄漏；"
        "第二组固定 Hamming 窗，只改变 taps 长度为 31、61 和 121，用于观察长度增加对频率选择性、固定群时延和计算量的影响。"
    )
    text += reporting.paragraph(
        "所有滤波器都采用相同采样率和近似低通规格，并统一计算通带波纹、阻带衰减、过渡带宽、固定群时延及逐样本乘加次数。"
        "其中固定群时延用于说明线性相位 FIR 的时域代价，乘加次数则用于表示实现复杂度。"
    )
    text += reporting.figure_block("固定 61 taps 时，不同窗函数的 FIR 低通响应比较。", p2e2["figure_window"])
    text += reporting.paragraph(rf"\input{{{p2e2['table_window']}}}")
    text += reporting.figure_block("固定 Hamming 时，不同 taps 长度的 FIR 低通响应比较。", p2e2["figure_length"])
    text += reporting.paragraph(rf"\input{{{p2e2['table_length']}}}")
    text += reporting.paragraph(r"\subsubsection*{分析与讨论}")
    text += reporting.paragraph(
        f"在固定 61 taps 的条件下，不同窗函数主要改变过渡带和阻带泄漏的分配方式。"
        f"Bartlett 窗的过渡带宽约为 {p2_window_rows['bartlett']['过渡带宽/Hz']:.2f} Hz，Hann 和 Hamming 分别约为 {p2_window_rows['hann']['过渡带宽/Hz']:.2f} Hz 与 {p2_window_rows['hamming']['过渡带宽/Hz']:.2f} Hz，"
        f"Blackman 则扩大到 {p2_window_rows['blackman']['过渡带宽/Hz']:.2f} Hz。"
        "图 8 的群时延子图中四条曲线完全重合，说明在同一 taps 长度下，线性相位 FIR 的固定延迟仅由长度决定，与窗函数种类无关。"
    )
    text += reporting.paragraph(
        f"在固定 Hamming 窗时，增加 taps 能系统改善频率选择性。taps 从 31 增加到 121 后，通带波纹由 {p2_length_rows[31]['通带波纹/dB']:.3f} dB 降到 {p2_length_rows[121]['通带波纹/dB']:.3f} dB，"
        f"阻带衰减由 {p2_length_rows[31]['阻带衰减/dB']:.2f} dB 提高到 {p2_length_rows[121]['阻带衰减/dB']:.2f} dB，过渡带宽则由 {p2_length_rows[31]['过渡带宽/Hz']:.2f} Hz 缩小到 {p2_length_rows[121]['过渡带宽/Hz']:.2f} Hz。"
        f"与此同时，固定群时延从 {p2_length_rows[31]['固定群时延/ms']:.0f} ms 增加到 {p2_length_rows[121]['固定群时延/ms']:.0f} ms，实现代价也从 {p2_length_rows[31]['实现代价/乘加每样本']:.0f} 增至 {p2_length_rows[121]['实现代价/乘加每样本']:.0f} 次乘加。"
    )
    text += reporting.paragraph(
        "因此，本实验展示了 FIR 设计中两条最基本但也最常见的权衡关系。"
        "一方面，窗口形状控制的是“主瓣宽度与旁瓣高度如何分配”；另一方面，滤波器长度控制的是“频率选择性、固定延迟和计算量如何同步变化”。"
        "在实际应用中，不能只追求阻带更深或过渡带更窄，而应结合系统延迟预算和运算资源共同决定窗口与长度。"
    )
    text += reporting.qa_block(
        "实验二思考题回答",
        [
            (
                "为什么矩形窗或三角窗往往更容易得到较窄的主瓣，但阻带泄漏却可能较大？",
                f"因为主瓣窄意味着时域截断更突然，对应频域旁瓣较高。实验中 Bartlett 窗的过渡带宽约为 {p2_window_rows['bartlett']['过渡带宽/Hz']:.2f} Hz，确实比 Blackman 更窄；"
                f"但其阻带衰减只有 {p2_window_rows['bartlett']['阻带衰减/dB']:.2f} dB，说明“主瓣窄、阻带脏”是典型权衡。"
            ),
            (
                "为什么布莱克曼窗通常能够更好地压低阻带泄漏，却往往牺牲过渡带宽度？",
                f"因为 Blackman 通过更强的时域加权压低旁瓣，代价是主瓣变宽。图 8 中它的过渡带约为 {p2_window_rows['blackman']['过渡带宽/Hz']:.2f} Hz，明显宽于 Hamming 的 {p2_window_rows['hamming']['过渡带宽/Hz']:.2f} Hz，"
                "因此同样长度下更容易以带宽为代价换取更平滑的阻带行为。"
            ),
            (
                "为什么增加 FIR 滤波器长度通常能改善频率选择性，但同时也会增加固定延迟和计算量？",
                f"更长的冲激响应提供了更高频率分辨率，因此过渡带更窄、阻带更深；本实验中从 31 taps 增到 121 taps 后，过渡带宽从 {p2_length_rows[31]['过渡带宽/Hz']:.2f} Hz 缩小到 {p2_length_rows[121]['过渡带宽/Hz']:.2f} Hz。"
                f"但群时延也按 $(L-1)/2$ 线性增长，从 {p2_length_rows[31]['固定群时延/ms']:.0f} ms 增到 {p2_length_rows[121]['固定群时延/ms']:.0f} ms，逐样本乘加次数同样成倍增加。"
            ),
            (
                "在窗函数法中，“过渡带更窄”和“阻带更干净”为什么往往不能同时做到都很理想？",
                f"因为它们分别对应主瓣宽度和旁瓣高度两个互相牵制的频域指标。以本实验为例，Hamming 窗把过渡带控制在约 {p2_window_rows['hamming']['过渡带宽/Hz']:.2f} Hz，"
                f"而 Blackman 通过更宽的 {p2_window_rows['blackman']['过渡带宽/Hz']:.2f} Hz 过渡带换取更平滑的阻带形态；单靠改变窗口形状，通常只能在“窄主瓣”和“低旁瓣”之间折中。"
            ),
        ],
    )

    text += reporting.paragraph(r"\subsection{实验三：FIR 与 IIR 带通滤波器在生物医学信号处理中的比较}")
    text += reporting.paragraph(r"\subsubsection*{实验方法}")
    text += reporting.paragraph(
        "按题面要求，真实 ERP 数据先从 250 Hz 重采样到 1000 Hz。FIR 方案采用等波纹逼近法，"
        f"通过 {p2e3['fir_hp_numtaps']} taps 的等波纹高通与 {p2e3['fir_lp_numtaps']} taps 的等波纹低通卷积得到线性相位带通，"
        f"整体长度为 {p2e3['fir_numtaps']} taps，对应固定群时延 {p2e3['fir_delay_samples']} 个样本（{p2e3['fir_delay_ms']:.2f} ms）。"
        "IIR 比较器采用题面指定的 4 阶 Butterworth 1--40 Hz 因果带通。"
        "两类滤波器都只做单次因果滤波，不用 filtfilt。"
    )
    text += reporting.paragraph(
        f"FIR 延迟补偿不再通过单纯修改横轴完成，而是将 FIR 滤波后的连续数据按触发点整体后移 {p2e3['fir_delay_samples']} 个样本后重新分段。"
        f"因此未经补偿的 FIR 保留试次为 {p2e3['fir_uncomp_kept']}，补偿后因边界效应保留试次为 {p2e3['fir_comp_kept']}（丢弃 {p2e3['fir_comp_dropped']}），"
        f"IIR 因果结果保留试次为 {p2e3['iir_kept']}。IIR 的通带群时延均值约为 {p2e3['iir_group_delay_mean_ms']:.2f} ms，标准差约为 {p2e3['iir_group_delay_std_ms']:.2f} ms。"
    )
    text += reporting.paragraph(
        "ERP 处理流程保持一致：对两个连续 Block 分别滤波，按目标试次触发点分段，进行双乳突重参考和基线校正，再合并求平均。"
        "在波形评价上，统一提取 Fz 导联 250--650 ms 区间内的主峰幅值与潜伏期，用于比较 FIR 未补偿、FIR 补偿后以及 IIR 因果实现之间的差别。"
    )
    text += reporting.figure_block("FIR 与 IIR 带通滤波器的频率响应、相位和群时延比较。", p2e3["figure_response"])
    text += reporting.paragraph(rf"\input{{{p2e3['table_filter']}}}")
    text += reporting.figure_block("未经补偿与经过固定延迟补偿后的 FIR/IIR 平均 ERP 比较。", p2e3["figure_erp"])
    text += reporting.paragraph(rf"\input{{{p2e3['table_erp']}}}")
    text += reporting.paragraph(r"\subsubsection*{分析与讨论}")
    text += reporting.paragraph(
        f"图 10 表明，FIR 与 IIR 的差异主要不在通带位置本身，而在相位特性和由此带来的时域解释。"
        f"FIR 方案的固定群时延为 {p2e3['fir_delay_ms']:.2f} ms，而 IIR 的通带群时延均值仅约 {p2e3['iir_group_delay_mean_ms']:.2f} ms，但标准差高达 {p2e3['iir_group_delay_std_ms']:.2f} ms。"
        "这意味着 IIR 的平均延迟较小，却无法用一个统一时间平移补偿所有频率成分；FIR 虽然延迟极大，但延迟结构稳定且可解释。"
    )
    text += reporting.paragraph(
        f"图 11 确凿地证实了这类相位差异必将直接且深刻地投射于最终叠加的 ERP 形态之上。值得高度警惕的是，在未经延迟补偿的 FIR 处理结果中，我们在观测窗内（{p2e3['fir_peak_latency_ms']:.0f} ms 处）捕获到的仅为约 1.34 uV 的微弱起伏。"
    )
    text += reporting.paragraph(
        f"这并非真实的 ERP 主峰被提前，而是因为长达 1900 ms 的巨大固定延迟，已经将真正的目标神经响应整体向后推迟到了观察窗口（-200 ms 至 800 ms）之外，当前残留在窗口内的不过是背景噪声或稳态视觉响应（SSVEP）的残余最大值。"
    )
    text += reporting.paragraph(
        f"而在执行了严格的整体时间补偿后，FIR 滤波器的真实形态得以完全复原，其真正的主峰精准落于 {p2e3['fir_comp_peak_latency_ms']:.0f} ms 处，峰值高达 9.83 uV；作为对比，IIR 因果滤波处理后的主峰潜伏期发生了不可逆的偏移，错位至约 {p2e3['iir_peak_latency_ms']:.0f} ms，且峰值受其相位色散的侵蚀，显著衰减至约 6.31 uV。"
    )
    text += reporting.paragraph(
        "这组强烈对比直观地揭示出：即便两类滤波器在频域上均严格限制在 1--40 Hz 的通带范围内，其截然迥异的相位特性依然会根本性地重塑叠加后信号的峰位、峰宽及幅值分布。"
    )
    text += reporting.paragraph(
        "从实验设计的角度看，这里比较的不是“哪一种滤波器绝对更优”，而是“哪一种误差更容易被解释和控制”。"
        "FIR 的代价是长度极长、固定延迟极大，但延迟结构明确，因此适合离线分析；"
        "IIR 的优势是实现紧凑、延迟更低，但其群时延分布不稳定，导致同样的 ERP 峰不能通过简单平移恢复。"
        "对于需要进行潜伏期解释的医学信号分析，这种差别具有直接的方法学意义。"
    )
    text += reporting.qa_block(
        "实验三思考题回答",
        [
            (
                "为什么线性相位 FIR 的延迟可以通过一个固定时间平移进行补偿，而 IIR 的相位失真通常不能用简单平移完全校正？",
                f"因为线性相位 FIR 在通带内所有频率共享同一个固定群时延，本实验中的固定延迟为 {p2e3['fir_delay_ms']:.2f} ms，因此可以通过“延后触发点再分段”等价地完成补偿。"
                f"图 11 中 FIR 主峰潜伏期正是从 {p2e3['fir_peak_latency_ms']:.0f} ms 回到 {p2e3['fir_comp_peak_latency_ms']:.0f} ms。"
                f"IIR 的通带群时延均值约为 {p2e3['iir_group_delay_mean_ms']:.2f} ms，标准差约为 {p2e3['iir_group_delay_std_ms']:.2f} ms，说明不同频率延迟不同，不能靠单一平移恢复原形。"
            ),
            (
                "如果两种滤波器的幅频响应已经比较接近，为什么平均 ERP 波形仍可能不同？",
                f"因为 ERP 的差异不仅由幅频选择性决定，还由相位和群时延决定。本实验中补偿后的 FIR 主峰潜伏期约为 {p2e3['fir_comp_peak_latency_ms']:.0f} ms，IIR 主峰则约为 {p2e3['iir_peak_latency_ms']:.0f} ms，"
                "说明两个滤波器即使在幅度上都保留 1--40 Hz，也会因对不同频率成分施加不同延迟而改变峰位和波形叠加结果。"
            ),
            (
                "为什么在高采样率、低高通截止频率的 ERP 场景中，FIR 带通滤波器往往会变得很长？",
                f"因为在 1000 Hz 采样率下，0.5 Hz 到 1 Hz 的过渡带只有 0.5 Hz，归一化过渡宽度极窄。为了同时满足 40 dB 阻带衰减和线性相位，FIR 需要 {p2e3['fir_numtaps']} taps，"
                f"对应固定群时延 {p2e3['fir_delay_ms']:.2f} ms，长度会迅速增大。"
            ),
            (
                "在离线分析、实时监测和嵌入式实现这三种场景下，FIR 与 IIR 各自更适合什么样的任务？为什么？",
                f"离线分析优先考虑形态保真和可解释补偿，FIR 更合适；本实验中它虽然有 {p2e3['fir_delay_ms']:.0f} ms 的巨大固定延迟，但可以明确补偿。"
                f"实时监测更在意低延迟，IIR 更现实，因为其平均群时延仅约 {p2e3['iir_group_delay_mean_ms']:.2f} ms；嵌入式实现又同时受限于算力和功耗，因此通常优先选低阶 IIR，除非任务必须严格保持相位。"
            ),
        ],
    )

    text += reporting.paragraph(r"\section{附录}")
    text += reporting.paragraph(
        r"提交压缩包“赵彦喆-3023006059.zip”包含三部分内容：完整实验报告 \path{medical_signal_filter_report.pdf}、"
        r"独立的一页结论摘要 \path{summary.pdf}，以及代码目录 \path{code/}。"
    )
    text += reporting.paragraph(
        r"其中，\path{code/scripts/} 提供实验入口和流程组织代码，可分别运行 Part-I、Part-II、报告生成与最终打包；"
        r"\path{code/medsiglab/} 提供数据读取、滤波器设计、ERP 处理、绘图和报告导出等底层函数；"
        r"\path{code/requirements.txt} 给出复现实验所需的 Python 依赖。该组织方式便于在不重跑全部内容的情况下单独调试某一部分实验、图表或文档。"
    )
    text += reporting.paragraph(
        r"代码复现步骤如下：首先将课程提供的原始数据目录“0 数据及例程/”放在项目根目录，确保其中包含 \path{sub7A.mat}、\path{64-channels.loc} 及示例程序；随后进入 \path{code/} 目录并安装依赖："
    )
    text += reporting.paragraph(r"\noindent\hspace*{2em}\texttt{pip install -r requirements.txt}")
    text += reporting.paragraph(
        r"如需一键复现实验全部结果，可执行："
    )
    text += reporting.paragraph(r"\noindent\hspace*{2em}\texttt{python3 scripts/run\_all.py}")
    text += reporting.paragraph(
        r"如只需重建报告，可执行："
    )
    text += reporting.paragraph(r"\noindent\hspace*{2em}\texttt{python3 scripts/build\_report.py}")
    text += reporting.paragraph(
        r"如需重新生成提交包，可执行："
    )
    text += reporting.paragraph(r"\noindent\hspace*{2em}\texttt{python3 scripts/package\_submission.py}")

    text += reporting.paragraph(r"\clearpage")
    text += reporting.paragraph(r"\section*{摘要}")
    text += reporting.paragraph(
        r"{\small 临床问题：为什么同一份脑电数据会因为滤波设置不同而出现不同峰位、不同波形，甚至影响解释。}"
    )
    text += reporting.paragraph(
        r"{\small 下图按 A--D 四个面板分别对应四个最关键的临床判断问题：同样的截止目标是否意味着相同代价、峰潜伏期能否被可靠保留、较高高通是否会改写晚期 ERP，以及不同滤波器的延迟是否能够被校正。}"
    )
    text += reporting.paragraph(r"{\captionsetup{font=footnotesize}")
    text += reporting.figure_block(
        "摘要图：A 为满足相同 40/60 Hz 低通指标时四类 IIR 设计的最低阶数及通带群时延，B 为因果与零相位低通对 10 Hz 峰位的影响，C 为 0.1--15 Hz 与 1.0--15 Hz 条件下 Fz 平均 ERP 的晚期成分差异，D 为补偿后 FIR 与因果 IIR 带通 ERP 波形及峰潜伏期差异。",
        metrics["summary_figure"],
        width="0.85\\linewidth",
        numbered=False,
    )
    text += reporting.paragraph(r"}")
    text += (
        r"{\small"
        "\n"
        r"\begin{itemize}[label=--,leftmargin=1.3em,itemsep=0.10em,topsep=0.15em,parsep=0pt]"
        "\n"
        r"\item \textbf{A 图：不同滤波器不是同一种工具。}在相同 40/60 Hz 低通目标下，Butterworth 需要 13 阶，而 Elliptic 只需 5 阶；它们都满足幅度指标，但通带群时延分别约为 37 ms 和 20 ms，说明实现同样的截止目标时，波形会承担不同的时间代价。"
        "\n"
        r"\item \textbf{B 图：零相位处理的价值在于保住峰位。}实验二中，单次因果低通把主要振荡推迟约 22 ms，重复因果后增至约 43 ms，而零相位处理基本保持 0 ms 延迟。对 ERP、诱发电位和心电波群这类依赖潜伏期判断的信号，这种差异足以改变解释。"
        "\n"
        r"\item \textbf{C 图：基线更平稳，不等于结果更真实。}当高通从 0.1--15 Hz 提高到 1.0--15 Hz 时，Fz 晚期正峰从 11.89 uV 降到 7.05 uV，300--700 ms 面积从 2.420 缩小到 0.765。也就是说，看起来更干净的基线，可能是以削弱晚期 ERP 成分为代价换来的。"
        "\n"
        r"\item \textbf{D 图：FIR 和 IIR 的差别还在于延迟能否解释。}本实验中 FIR 固定延迟为 1900 ms，但整体补偿后主峰可回到约 479 ms；IIR 因频率依赖延迟不同，主峰仍约在 399 ms，不能用单一时间平移完整校正。因此，同样是带通后的波形，其时间位置未必具有同样的临床含义。"
        "\n"
        r"\end{itemize}"
        "\n"
        r"}"
        "\n"
    )
    text += reporting.paragraph(
        r"{\small \textbf{临床提醒：}滤波不会凭空创造疾病信息，但会改变峰值、潜伏期和慢波强弱的呈现方式。阅读 ERP、诱发电位或其他生物电结果时，应同时核对截止频率、滤波器类型、是否零相位以及是否做延迟补偿；若参数过强或描述不清，应进一步查看原始波形、较温和参数结果和补偿前后对照。}"
    )
    return reporting.apply_cjk_font(
        text.replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("μ", "u")
    )


def write_report(metrics: dict) -> Path:
    config.REPORT_BODY_TEX.write_text(build_report_body(metrics), encoding="utf-8")
    return reporting.compile_report()


def load_metrics(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build report PDF from an existing metrics JSON file.")
    parser.add_argument("--metrics", default=str(config.REPORT_OUTPUT_DIR / "metrics.json"))
    args = parser.parse_args(argv)

    metrics_path = Path(args.metrics)
    metrics = load_metrics(metrics_path)
    pdf_path = write_report(metrics)
    print(json.dumps({"report_pdf": str(pdf_path), "metrics_json": str(metrics_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
