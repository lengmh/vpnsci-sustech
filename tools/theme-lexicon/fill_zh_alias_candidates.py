"""Fill review-gated Chinese alias candidates for English concepts.

This is an offline maintenance step for L3. It does not accept aliases into the
runtime overlay. It only fills ``zh_alias_candidates`` when an exact bilingual
glossary or conservative compositional technical pattern can produce a plausible
Chinese term. Exact glossary hits are high confidence; compositional candidates
remain review-gated. Source-prioritized concepts are filled first, but the same
review-gated conservative rules may also fill non-priority sources to improve
full English concept-set coverage. Ambiguous concepts remain pending for later
host-Agent review.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable

PRIORITY_SOURCES = {"cso", "ieee_taxonomy", "openalex_topics"}
TECHNICAL_PRIORITY_DOMAINS = {
    "antennas_and_propagation",
    "circuits_and_systems",
    "communications_technology",
    "computational_and_artificial_intelligence",
    "computer_science",
    "control_systems",
    "electron_devices",
    "engineering",
    "instrumentation_and_measurement",
    "mathematics",
    "physical_sciences",
    "power_engineering_and_energy",
    "robotics_and_automation",
    "signal_processing",
    "systems_engineering_and_theory",
}
DEFAULT_MAX_CANDIDATES = 3
GENERATED_STATUSES = {
    "high_confidence_generated",
    "source_priority_generated",
    "conservative_generated",
}

GENERIC_EN = {
    "analysis",
    "application",
    "applications",
    "case",
    "data",
    "education",
    "method",
    "methods",
    "model",
    "models",
    "research",
    "study",
    "studies",
    "system",
    "systems",
}

GENERIC_ZH = {
    "分析",
    "应用",
    "案例",
    "方法",
    "模型",
    "数据",
    "研究",
    "系统",
}

BIOMEDICAL_COMPOSITION_BLOCKLIST = {
    "fiber",
    "fibers",
    "emission",
    "emissions",
    "cellular",
    "machine",
    "machines",
}

RAW_EXACT_ALIASES = {
    "0 1 knapsack problem": "0-1背包问题",
    "0/1 knapsack problem": "0-1背包问题",
    "1 f noise": "1/f噪声",
    "2 d discrete wavelet transform": "二维离散小波变换",
    "2 d model": "二维模型",
    "2 dof": "2自由度",
    "2d video": "二维视频",
    "3 axis accelerometer": "三轴加速度计",
    "3 d display": "三维显示",
    "3 d imaging": "三维成像",
    "3 d integrated circuit": "三维集成电路",
    "3 d reconstruction": "三维重建",
    "3 d virtual environment": "三维虚拟环境",
    "3 dof": "3自由度",
    "3d audio": "3D音频",
    "3d face recognition": "3D人脸识别",
    "3d face reconstruction": "3D人脸重建",
    "3d graphics": "三维图形",
    "3d model retrieval": "三维模型检索",
    "3d object": "三维对象",
    "3d object recognition": "三维目标识别",
    "3d object retrieval": "三维目标检索",
    "3d pose estimation": "三维姿态估计",
    "3d printing": "3D打印",
    "3d scanning": "三维扫描",
    "3d shape modeling and analysis": "三维形状建模与分析",
    "3d user interface": "三维用户界面",
    "3d video coding": "三维视频编码",
    "3d visualization": "三维可视化",
    "3g cellular network": "3G蜂窝网络",
    "3g mobile communication": "3G移动通信",
    "3g mobile communication system": "3G移动通信系统",
    "3g mobile": "3G移动通信",
    "3gpp lte": "3GPP LTE",
    "4g mobile communication": "4G移动通信",
    "4g mobile communication system": "4G移动通信系统",
    "5g mobile communication": "5G移动通信",
    "6g mobile communication": "6G移动通信",
    "8 bit microcontroller": "8位微控制器",
    "16s rrna": "16S核糖体RNA",
    "18s rrna": "18S核糖体RNA",
    "28s rrna": "28S核糖体RNA",
    "100 silicon": "(100)硅",
    "1064 nm": "1064纳米",
    "1db compression point": "1dB压缩点",
    "ad hoc network": "自组织网络",
    "abstract algebra": "抽象代数",
    "access control": "访问控制",
    "access control mechanism": "访问控制机制",
    "abdominal vascular conditions and treatments": "腹部血管疾病与治疗",
    "adaptive control": "自适应控制",
    "adaptive dynamic programming": "自适应动态规划",
    "adaptive mesh refinement": "自适应网格加密",
    "adaptive optics": "自适应光学",
    "adrenergic beta receptor": "肾上腺素能β受体",
    "anomaly detection": "异常检测",
    "antenna array": "天线阵列",
    "attention deficit hyperactivity disorder": "注意缺陷多动障碍",
    "artificial intelligence": "人工智能",
    "association rule mining": "关联规则挖掘",
    "autonomous driving": "自动驾驶",
    "autonomous vehicle": "自动驾驶车辆",
    "bayesian network": "贝叶斯网络",
    "beamforming": "波束成形",
    "big data": "大数据",
    "blockchain": "区块链",
    "channel estimation": "信道估计",
    "channel state information": "信道状态信息",
    "classification": "分类",
    "cloud computing": "云计算",
    "clustering": "聚类",
    "cognitive radio": "认知无线电",
    "communication system": "通信系统",
    "computer vision": "计算机视觉",
    "control system": "控制系统",
    "convolutional neural network": "卷积神经网络",
    "convex optimization": "凸优化",
    "cryptography": "密码学",
    "cyber security": "网络安全",
    "data mining": "数据挖掘",
    "database": "数据库",
    "decision tree": "决策树",
    "deep learning": "深度学习",
    "digital signal processing": "数字信号处理",
    "discrete wavelet transform": "离散小波变换",
    "dna repair": "DNA修复",
    "differential diagnosis": "鉴别诊断",
    "distributed system": "分布式系统",
    "dynamic programming": "动态规划",
    "edge computing": "边缘计算",
    "electric vehicle": "电动汽车",
    "energy storage": "储能",
    "error correction": "纠错",
    "face recognition": "人脸识别",
    "fault diagnosis": "故障诊断",
    "feature extraction": "特征提取",
    "federated learning": "联邦学习",
    "fiber optic sensor": "光纤传感器",
    "genetic algorithm": "遗传算法",
    "graph neural network": "图神经网络",
    "graph theory": "图论",
    "hidden markov model": "隐马尔可夫模型",
    "image classification": "图像分类",
    "image processing": "图像处理",
    "image segmentation": "图像分割",
    "information retrieval": "信息检索",
    "internet of things": "物联网",
    "intrusion detection": "入侵检测",
    "knowledge graph": "知识图谱",
    "medical education": "医学教育",
    "license plate recognition": "车牌识别",
    "linear programming": "线性规划",
    "long term evolution": "长期演进",
    "localization": "定位",
    "machine learning": "机器学习",
    "markov decision process": "马尔可夫决策过程",
    "microgrid": "微电网",
    "mimo": "多输入多输出",
    "mobile ad hoc network": "移动自组织网络",
    "motion planning": "运动规划",
    "natural language processing": "自然语言处理",
    "neural network": "神经网络",
    "network security": "网络安全",
    "object detection": "目标检测",
    "ofdm": "正交频分复用",
    "ontology": "本体",
    "optimal control": "最优控制",
    "optimization": "优化",
    "particle swarm optimization": "粒子群优化",
    "path planning": "路径规划",
    "pattern recognition": "模式识别",
    "pid control": "PID控制",
    "positioning": "定位",
    "power system": "电力系统",
    "predictive maintenance": "预测性维护",
    "principal component analysis": "主成分分析",
    "privacy preserving": "隐私保护",
    "quantum computing": "量子计算",
    "radio frequency": "射频",
    "random forest": "随机森林",
    "reconfigurable intelligent surface": "可重构智能表面",
    "receptor adrenergic beta": "肾上腺素能β受体",
    "recommendation system": "推荐系统",
    "recommender system": "推荐系统",
    "regression": "回归",
    "reinforcement learning": "强化学习",
    "renewable energy": "可再生能源",
    "robotics": "机器人学",
    "robust control": "鲁棒控制",
    "semantic web": "语义网",
    "semi supervised learning": "半监督学习",
    "sensor fusion": "传感器融合",
    "sensor network": "传感器网络",
    "shortest path": "最短路径",
    "signal processing": "信号处理",
    "simulated annealing": "模拟退火",
    "smart grid": "智能电网",
    "speech recognition": "语音识别",
    "spectrum sensing": "频谱感知",
    "supervised learning": "监督学习",
    "support vector machine": "支持向量机",
    "target detection": "目标检测",
    "text classification": "文本分类",
    "transfer learning": "迁移学习",
    "unmanned aerial vehicle": "无人机",
    "unsupervised learning": "无监督学习",
    "uav": "无人机",
    "vanet": "车载自组织网络",
    "v2x": "车联网",
    "vehicle detection": "车辆检测",
    "vehicle license plate recognition": "车牌识别",
    "vehicle routing": "车辆路径",
    "vehicle routing problem": "车辆路径问题",
    "vehicle routing problem with time window": "带时间窗车辆路径问题",
    "vehicle to everything": "车联网",
    "vehicle to grid": "车网互动",
    "vehicle to infrastructure": "车路通信",
    "vehicle to vehicle communication": "车车通信",
    "vehicle tracking": "车辆跟踪",
    "vehicular ad hoc network": "车载自组织网络",
    "wireless communication": "无线通信",
    "wireless power transfer": "无线电能传输",
    "wireless sensor network": "无线传感器网络",
}

RAW_COMPONENTS = {
    "2 d": "二维",
    "2d": "二维",
    "3 d": "三维",
    "3d": "三维",
    "3 g": "3G",
    "3g": "3G",
    "4 g": "4G",
    "4g": "4G",
    "5 g": "5G",
    "5g": "5G",
    "6 g": "6G",
    "6g": "6G",
    "802 11": "802.11",
    "abstract": "抽象",
    "abdominal": "腹部",
    "abrasive": "磨料",
    "absolute": "绝对",
    "absorption": "吸收",
    "absorbing": "吸收",
    "accelerated": "加速",
    "acceleration": "加速度",
    "accelerator": "加速器",
    "accelerometer": "加速度计",
    "access": "访问",
    "accessibility": "可访问性",
    "accounting": "会计",
    "accuracy": "精度",
    "acute": "急性",
    "adaptive": "自适应",
    "adrenergic": "肾上腺素能",
    "additive": "增材",
    "advanced": "先进",
    "adversarial": "对抗",
    "aerospace": "航空航天",
    "aging": "老化",
    "affinity": "亲和",
    "algebra": "代数",
    "algebraic": "代数",
    "algorithm": "算法",
    "algorithmic": "算法",
    "application": "应用",
    "applications": "应用",
    "architecture": "架构",
    "argumentation": "论证",
    "antenna": "天线",
    "audio": "音频",
    "authentication": "认证",
    "autonomous": "自主",
    "battery": "电池",
    "bayesian": "贝叶斯",
    "biomedical": "生物医学",
    "biosensor": "生物传感器",
    "biosorption": "生物吸附",
    "beta": "β",
    "bit": "位",
    "boundary": "边界",
    "cellular": "蜂窝",
    "channel": "信道",
    "chemical": "化学",
    "circuit": "电路",
    "classification": "分类",
    "cloud": "云",
    "coding": "编码",
    "combinatorial": "组合",
    "coefficient": "系数",
    "communication": "通信",
    "composite": "复合",
    "condition": "条件",
    "complication": "并发症",
    "compression": "压缩",
    "computing": "计算",
    "computer": "计算机",
    "content": "内容",
    "convolutional": "卷积",
    "converter": "转换器",
    "control": "控制",
    "dc dc": "DC-DC",
    "design": "设计",
    "data": "数据",
    "deep": "深度",
    "detection": "检测",
    "diagnosis": "诊断",
    "differential": "微分",
    "digital": "数字",
    "discrete": "离散",
    "dna": "DNA",
    "disorder": "障碍",
    "display": "显示",
    "distributed": "分布式",
    "dynamic": "动态",
    "dynamics": "动力学",
    "edge": "边缘",
    "electric": "电动",
    "electrical": "电气",
    "education": "教育",
    "energy": "能源",
    "engineering": "工程",
    "environmental": "环境",
    "enzyme": "酶",
    "estimation": "估计",
    "evaluation": "评估",
    "face": "人脸",
    "factor": "因子",
    "fault": "故障",
    "feature": "特征",
    "federated": "联邦",
    "fiber": "光纤",
    "fiber optic": "光纤",
    "filtering": "滤波",
    "financial": "财务",
    "friction": "摩擦",
    "frequency": "频率",
    "geometric": "几何",
    "geometry": "几何",
    "geospatial": "地理空间",
    "governance": "治理",
    "graph": "图",
    "graphic": "图形",
    "graphics": "图形",
    "grid": "电网",
    "harmonic": "调和",
    "health": "健康",
    "high": "高",
    "historical": "历史",
    "history": "历史",
    "human": "人类",
    "image": "图像",
    "imaging": "成像",
    "information": "信息",
    "interaction": "相互作用",
    "integrated": "集成",
    "integrated circuit": "集成电路",
    "intelligent": "智能",
    "interface": "界面",
    "interpretation": "解释",
    "internet": "互联网",
    "intrusion": "入侵",
    "iot": "物联网",
    "learning": "学习",
    "license plate": "车牌",
    "localization": "定位",
    "logistics": "物流",
    "low": "低",
    "lte": "LTE",
    "machine": "机器",
    "machining": "加工",
    "management": "管理",
    "manufacturing": "制造",
    "material": "材料",
    "mathematical": "数学",
    "mathematics": "数学",
    "measurement": "测量",
    "mechanism": "机制",
    "medical": "医学",
    "memory": "存储",
    "mesh": "网格",
    "metasurface": "超表面",
    "microcontroller": "微控制器",
    "mobile": "移动",
    "modeling": "建模",
    "monitoring": "监测",
    "motor": "电机",
    "multi agent": "多智能体",
    "natural language": "自然语言",
    "nonlinear": "非线性",
    "network": "网络",
    "neural": "神经",
    "noise": "噪声",
    "object": "目标",
    "operator": "算子",
    "organizational": "组织",
    "optimal": "最优",
    "optical": "光学",
    "optic": "光学",
    "optics": "光学",
    "particle swarm": "粒子群",
    "path": "路径",
    "physical": "物理",
    "physics": "物理",
    "permission": "权限",
    "policy": "策略",
    "pose": "姿态",
    "power": "电力",
    "prevention": "预防",
    "printer": "打印机",
    "printing": "打印",
    "process": "过程",
    "processing": "处理",
    "protein": "蛋白",
    "protocol": "协议",
    "psychology": "心理学",
    "publishing": "出版",
    "privacy": "隐私",
    "quantum": "量子",
    "radio frequency": "射频",
    "random": "随机",
    "recognition": "识别",
    "reconstruction": "重建",
    "receptor": "受体",
    "reinforcement": "强化",
    "repair": "修复",
    "research": "研究",
    "resonator": "谐振器",
    "retrieval": "检索",
    "robust": "鲁棒",
    "routing": "路由",
    "scanning": "扫描",
    "scene": "场景",
    "scientific": "科学",
    "security": "安全",
    "semantic": "语义",
    "sensor": "传感器",
    "service": "服务",
    "shape": "形状",
    "signal": "信号",
    "silicon": "硅",
    "simulation": "仿真",
    "smart": "智能",
    "speech": "语音",
    "stabilization": "稳定",
    "statistical": "统计",
    "storage": "存储",
    "structure": "结构",
    "surgery": "手术",
    "surface": "表面",
    "surveying": "测量",
    "syntax": "语法",
    "synthesis": "合成",
    "spectrum": "频谱",
    "support vector": "支持向量",
    "technique": "技术",
    "technology": "技术",
    "theory": "理论",
    "target": "目标",
    "text": "文本",
    "topology": "拓扑",
    "traffic": "交通",
    "transcription": "转录",
    "transport": "转运",
    "trauma": "创伤",
    "treatment": "治疗",
    "trust": "信任",
    "transfer": "迁移",
    "transform": "变换",
    "tsv": "硅通孔",
    "user": "用户",
    "vehicle": "车辆",
    "vehicular": "车载",
    "video": "视频",
    "virtual": "虚拟",
    "virtual environment": "虚拟环境",
    "visualization": "可视化",
    "vision": "视觉",
    "vascular": "血管",
    "wave": "波",
    "wavefront": "波前",
    "wavelet": "小波",
    "wireless": "无线",
}

SUFFIX_PATTERNS = [
    ("routing problem with time window", "路径问题"),
    ("routing problem", "路径问题"),
    ("ad hoc network", "自组织网络"),
    ("neural network", "神经网络"),
    ("sensor network", "传感器网络"),
    ("communication system", "通信系统"),
    ("control system", "控制系统"),
    ("support vector machine", "支持向量机"),
    ("state information", "状态信息"),
    ("integrated circuit", "集成电路"),
    ("user interface", "用户界面"),
    ("virtual environment", "虚拟环境"),
    ("mobile communication", "移动通信"),
    ("mobile communication system", "移动通信系统"),
    ("cellular network", "蜂窝网络"),
    ("wavelet transform", "小波变换"),
    ("discrete wavelet transform", "离散小波变换"),
    ("classification", "分类"),
    ("segmentation", "分割"),
    ("recognition", "识别"),
    ("detection", "检测"),
    ("estimation", "估计"),
    ("prediction", "预测"),
    ("optimization", "优化"),
    ("processing", "处理"),
    ("analysis", "分析"),
    ("control", "控制"),
    ("routing", "路由"),
    ("planning", "规划"),
    ("sensing", "感知"),
    ("fusion", "融合"),
    ("retrieval", "检索"),
    ("reconstruction", "重建"),
    ("visualization", "可视化"),
    ("simulation", "仿真"),
    ("monitoring", "监测"),
    ("diagnosis", "诊断"),
    ("management", "管理"),
    ("repair", "修复"),
    ("interaction", "相互作用"),
    ("transcription factor", "转录因子"),
    ("manufacturing", "制造"),
    ("modeling", "建模"),
    ("imaging", "成像"),
    ("coding", "编码"),
    ("design", "设计"),
    ("measurement", "测量"),
    ("authentication", "认证"),
    ("printing", "打印"),
    ("scanning", "扫描"),
    ("network", "网络"),
    ("system", "系统"),
    ("structure", "结构"),
    ("architecture", "架构"),
    ("protocol", "协议"),
    ("material", "材料"),
    ("technology", "技术"),
    ("technique", "技术"),
    ("algorithm", "算法"),
    ("method", "方法"),
    ("model", "模型"),
    ("application", "应用"),
    ("research", "研究"),
    ("study", "研究"),
    ("process", "过程"),
    ("theory", "理论"),
    ("problem", "问题"),
]

RAW_EXACT_ALIASES.update(
    {
        "3gpp": "第三代合作伙伴计划",
        "3gpp lte": "3GPP LTE通信",
        "3rd generation partnership project 3gpp": "第三代合作伙伴计划",
        "4g": "4G通信",
        "5 dof": "5自由度",
        "5-dof": "5自由度",
        "6 dof": "6自由度",
        "6-dof": "6自由度",
        "6lowpan": "IPv6低功耗无线个域网",
        "active appearance model": "主动外观模型",
        "active contour": "主动轮廓",
        "active contour method": "主动轮廓方法",
        "active learning": "主动学习",
        "active noise control": "主动噪声控制",
        "active pixel sensor": "有源像素传感器",
        "active queue management": "主动队列管理",
        "active rfid": "有源RFID",
        "active suspension": "主动悬架",
        "ac motor": "AC电机",
        "ac motors": "AC电机",
        "ac power transmission": "交流输电",
        "actor critic": "Actor-Critic",
        "actor critic algorithm": "Actor-Critic算法",
        "actuator": "执行器",
        "actuators": "执行器",
        "action potential": "动作电位",
        "action potentials": "动作电位",
        "action recognition": "动作识别",
        "action selection": "动作选择",
        "action sequence": "动作序列",
        "action sequences": "动作序列",
        "action unit": "动作单元",
        "ad hoc on demand distance vector": "自组织按需距离向量",
        "ad hoc routing protocol": "自组织路由协议",
        "ad hoc wireless network": "自组织无线网络",
        "adrenal gland": "肾上腺",
        "adrenal gland disease": "肾上腺疾病",
        "adrenal gland diseases": "肾上腺疾病",
        "activity diagram": "活动图",
        "adaptive equalizer": "自适应均衡器",
        "adaptive kalman filter": "自适应卡尔曼滤波器",
        "adaptive resource allocation": "自适应资源分配",
        "adaptive streaming": "自适应流媒体",
        "air quality": "空气质量",
        "agent based": "基于智能体",
        "analytical hierarchy process": "层次分析法",
        "analytic hierarchy process": "层次分析法",
        "ant colony optimization": "蚁群优化",
        "auto encoder": "自编码器",
        "auto encoders": "自编码器",
        "bile duct": "胆管",
        "bile duct disease": "胆管疾病",
        "bile duct diseases": "胆管疾病",
        "biliary tract": "胆道",
        "biliary tract surgical procedure": "胆道外科手术",
        "biliary tract surgical procedures": "胆道外科手术",
        "brain computer interface": "脑机接口",
        "border gateway protocol": "边界网关协议",
        "brain death": "脑死亡",
        "capability maturity model": "能力成熟度模型",
        "carotid artery": "颈动脉",
        "carotid artery disease": "颈动脉疾病",
        "carotid artery diseases": "颈动脉疾病",
        "carotid artery injury": "颈动脉损伤",
        "carotid artery injuries": "颈动脉损伤",
        "cell death": "细胞死亡",
        "chosen ciphertext attack": "选择密文攻击",
        "common bile duct": "胆总管",
        "common bile duct disease": "胆总管疾病",
        "common bile duct diseases": "胆总管疾病",
        "core binding factor": "核心结合因子",
        "core binding factor alpha 1 subunit": "核心结合因子α1亚基",
        "core binding factor alpha 2 subunit": "核心结合因子α2亚基",
        "core binding factor alpha 3 subunit": "核心结合因子α3亚基",
        "core binding factor alpha subunit": "核心结合因子α亚基",
        "core binding factor beta subunit": "核心结合因子β亚基",
        "common information model": "公共信息模型",
        "abc algorithm": "人工蜂群算法",
        "aco algorithm": "蚁群优化算法",
        "aperture radar": "孔径雷达",
        "bit rate": "比特率",
        "cancer treatment": "癌症治疗",
        "climate change": "气候变化",
        "code division multiple access": "码分多址",
        "computer aided": "计算机辅助",
        "computer assisted": "计算机辅助",
        "computed tomography": "计算机断层成像",
        "computer numerical control": "计算机数控",
        "context aware": "上下文感知",
        "context aware service": "上下文感知服务",
        "corporate social responsibility": "企业社会责任",
        "covid 19": "COVID-19",
        "cytochrome p 450": "细胞色素P450",
        "cytochrome p 450 cyp1a2 inhibitor": "细胞色素P450 CYP1A2抑制剂",
        "cytochrome p 450 cyp2d6 inhibitor": "细胞色素P450 CYP2D6抑制剂",
        "cytochrome p 450 cyp3a inhibitor": "细胞色素P450 CYP3A抑制剂",
        "delay locked loop": "延迟锁定环",
        "denial of service": "拒绝服务",
        "denial of service attack": "拒绝服务攻击",
        "delta modulation": "增量调制",
        "delta sigma modulation": "Δ-Σ调制",
        "delta sigma modulator": "Δ-Σ调制器",
        "direction of arrival": "到达方向",
        "direction of arrival estimation": "到达方向估计",
        "decision making": "决策",
        "decision support system": "决策支持系统",
        "differential equation": "微分方程",
        "division multiple access": "多址接入",
        "division multiplexing": "分复用",
        "e learning": "电子学习",
        "electronic medical record": "电子病历",
        "enterprise resource planning": "企业资源计划",
        "energy harvesting": "能量采集",
        "erbium doped fiber": "掺铒光纤",
        "erbium doped": "掺铒",
        "erbium doped fiber amplifier": "掺铒光纤放大器",
        "erbium doped fiber amplifier edfa": "掺铒光纤放大器（EDFA）",
        "erbium doped fiber laser": "掺铒光纤激光器",
        "fading channel": "衰落信道",
        "fault tolerant": "容错",
        "fault tolerant control": "容错控制",
        "fourier transform": "傅里叶变换",
        "frequency division": "频分",
        "fuzzy inference system": "模糊推理系统",
        "geographic information system": "地理信息系统",
        "gtp binding protein": "GTP结合蛋白",
        "gtp binding protein alpha subunit": "GTP结合蛋白α亚基",
        "gtp binding protein beta subunit": "GTP结合蛋白β亚基",
        "gtp binding protein gamma subunit": "GTP结合蛋白γ亚基",
        "gap junction alpha 4 protein": "缝隙连接α4蛋白",
        "gap junction alpha 5 protein": "缝隙连接α5蛋白",
        "gap junction beta 1 protein": "缝隙连接β1蛋白",
        "gap junction delta 2 protein": "缝隙连接δ2蛋白",
        "field programmable gate array": "现场可编程门阵列",
        "fuzzy logic": "模糊逻辑",
        "h 264": "H.264",
        "h 264 avc": "H.264/AVC",
        "heterojunction bipolar transistor": "异质结双极晶体管",
        "higher education": "高等教育",
        "hla dp antigen": "HLA-DP抗原",
        "hla dq antigen": "HLA-DQ抗原",
        "hla dr antigen": "HLA-DR抗原",
        "human right": "人权",
        "impulse response": "脉冲响应",
        "information system": "信息系统",
        "kalman filter": "卡尔曼滤波器",
        "k nearest neighbor": "K近邻",
        "k nearest neighbor algorithm": "K近邻算法",
        "k nearest neighbor classifier": "K近邻分类器",
        "k nn": "K近邻",
        "k nn algorithm": "K近邻算法",
        "k nn classifier": "K近邻分类器",
        "k nn query": "K近邻查询",
        "kidney disease": "肾脏疾病",
        "kidney diseases": "肾脏疾病",
        "latin america": "拉丁美洲",
        "latin american": "拉丁美洲",
        "light emitting diode": "发光二极管",
        "liver disease": "肝脏疾病",
        "liver diseases": "肝脏疾病",
        "large scale integration": "大规模集成",
        "land mobile radio": "陆地移动无线电",
        "localization and mapping": "定位与建图",
        "magnetic resonance": "磁共振",
        "magnetic resonance imaging": "磁共振成像",
        "markov chain": "马尔可夫链",
        "meta heuristic method": "元启发式方法",
        "meta heuristic": "元启发式",
        "mitochondrial trifunctional protein": "线粒体三功能蛋白",
        "mitochondrial trifunctional protein alpha subunit": "线粒体三功能蛋白α亚基",
        "mitochondrial trifunctional protein beta subunit": "线粒体三功能蛋白β亚基",
        "mobile ad hoc": "移动自组织网络",
        "maximum likelihood": "最大似然",
        "mean square": "均方",
        "mean square error": "均方误差",
        "mental health": "心理健康",
        "millimeter wave": "毫米波",
        "mobile radio": "移动无线电",
        "monte carlo": "蒙特卡罗",
        "multi hop": "多跳",
        "multi objective": "多目标",
        "multiple input multiple output": "多输入多输出",
        "multiple access": "多址接入",
        "navier stoke equation": "纳维-斯托克斯方程",
        "nearest neighbor": "最近邻",
        "object oriented": "面向对象",
        "occupational health": "职业健康",
        "optical fiber": "光纤",
        "orthogonal frequency division": "正交频分",
            "particle beam": "粒子束",
            "petri net": "Petri网",
            "petri nets": "Petri网",
        "phase locked loop": "锁相环",
        "phase shift keying": "相移键控",
        "physical unclonable function": "物理不可克隆函数",
        "programmable gate array": "可编程门阵列",
        "pulse width": "脉冲宽度",
        "pulse width modulation": "脉冲宽度调制",
        "power generation": "发电",
        "power system": "电力系统",
        "power supply": "电源",
        "public health": "公共卫生",
        "quantum well": "量子阱",
        "rate distortion": "率失真",
        "real time": "实时",
        "refractive index": "折射率",
        "retinal disease": "视网膜疾病",
        "retinal diseases": "视网膜疾病",
        "remote sensing": "遥感",
        "signal to noise ratio": "信噪比",
        "sliding mode": "滑模",
        "sliding mode control": "滑模控制",
        "software development": "软件开发",
        "solid state": "固态",
        "source separation": "源分离",
        "spread spectrum": "扩频",
        "sigma delta modulation": "Σ-Δ调制",
        "sigma delta modulator": "Σ-Δ调制器",
        "system on chip": "片上系统",
        "synthetic aperture": "合成孔径",
        "synthetic aperture radar": "合成孔径雷达",
        "takagi sugeno fuzzy model": "Takagi-Sugeno模糊模型",
        "takagi sugeno fuzzy system": "Takagi-Sugeno模糊系统",
        "takagi sugeno model": "Takagi-Sugeno模型",
        "thin film": "薄膜",
        "three dimensional": "三维",
        "time varying": "时变",
        "third generation partnership project": "第三代合作伙伴计划",
        "ultra wideband": "超宽带",
        "ultrasonography carotid artery": "颈动脉超声检查",
        "vehicular ad hoc network vanet": "车载自组织网络",
        "wireless sensor network": "无线传感器网络",
        "video streaming": "视频流",
        "wide area": "广域",
        "wide area network": "广域网",
        "x ray": "X射线",
    }
)

RAW_COMPONENTS.update(
    {
        "academic": "学术",
        "accident": "事故",
        "achievement": "成就",
        "acoustic": "声学",
        "acoustical": "声学",
        "activity": "活动",
        "agent": "智能体",
        "agricultural": "农业",
        "agriculture": "农业",
        "alloy": "合金",
        "amplifier": "放大器",
        "analysis": "分析",
        "analyses": "分析",
        "analytical": "分析",
        "ant": "蚁",
        "array": "阵列",
        "assessment": "评估",
        "attack": "攻击",
        "automatic": "自动",
        "band": "频带",
        "beam": "波束",
        "behavior": "行为",
        "border": "边界",
        "biological": "生物",
        "biology": "生物学",
        "business": "商业",
        "capability": "能力",
        "cancer": "癌症",
        "carbon": "碳",
        "career": "职业",
        "category": "类别",
        "cell": "细胞",
        "century": "世纪",
        "charge": "费用",
        "chemistry": "化学",
        "ciphertext": "密文",
        "climate": "气候",
        "code": "代码",
        "cognitive": "认知",
        "colony": "群",
        "color": "颜色",
        "component": "组件",
        "compound": "化合物",
        "computational": "计算",
        "controller": "控制器",
        "cultural": "文化",
        "culture": "文化",
        "database": "数据库",
        "decision": "决策",
        "delay": "延迟",
        "detector": "探测器",
        "development": "发展",
        "device": "设备",
        "disease": "疾病",
        "distribution": "分布",
        "diverse": "多样",
        "diversity": "多样性",
        "domain": "域",
        "ecology": "生态学",
        "economic": "经济",
        "educational": "教育",
        "effect": "效应",
        "electromagnetic": "电磁",
        "electronic": "电子",
        "electron": "电子",
        "engine": "引擎",
        "encoder": "编码器",
        "environment": "环境",
        "equipment": "设备",
        "equation": "方程",
        "error": "错误",
        "feedback": "反馈",
        "field": "场",
        "film": "薄膜",
        "filter": "滤波器",
        "finite": "有限",
        "flow": "流",
        "food": "食品",
        "freedom": "自由",
        "function": "函数",
        "fusion": "融合",
        "fuzzy": "模糊",
        "game": "博弈",
        "gateway": "网关",
        "gaussian": "高斯",
        "generation": "生成",
        "genetic": "遗传",
        "global": "全球",
        "governance": "治理",
        "healthcare": "医疗保健",
        "heritage": "遗产",
        "identity": "身份",
        "ieee": "IEEE",
        "impact": "影响",
        "index": "索引",
        "indexing": "索引",
        "industrial": "工业",
        "industry": "产业",
        "innovation": "创新",
        "intelligence": "智能",
        "interference": "干扰",
        "integration": "集成",
        "integrity": "诚信",
        "issue": "问题",
        "key": "密钥",
        "knowledge": "知识",
        "language": "语言",
        "laser": "激光",
        "law": "法律",
        "legal": "法律",
        "level": "级别",
        "library": "图书馆",
        "light": "光",
        "line": "线",
        "linear": "线性",
        "literature": "文献",
        "logic": "逻辑",
        "magnet": "磁体",
        "magnetic": "磁",
        "marine": "海洋",
        "matrix": "矩阵",
        "mechanical": "机械",
        "media": "媒体",
        "method": "方法",
        "microwave": "微波",
        "mining": "挖掘",
        "mode": "模式",
        "model": "模型",
        "modulation": "调制",
        "molecular": "分子",
        "motion": "运动",
        "multi": "多",
        "multiple": "多重",
        "natural": "自然",
        "navigation": "导航",
        "node": "节点",
        "nuclear": "核",
        "open": "开放",
        "packet": "分组",
        "parallel": "并行",
        "parameter": "参数",
        "partnership": "合作伙伴",
        "pattern": "模式",
        "performance": "性能",
        "phase": "相位",
        "philosophy": "哲学",
        "plasma": "等离子体",
        "planning": "规划",
        "plant": "植物",
        "point": "点",
        "political": "政治",
        "politics": "政治",
        "practice": "实践",
        "problem": "问题",
        "production": "生产",
        "program": "程序",
        "programming": "编程",
        "project": "项目",
        "propagation": "传播",
        "property": "性质",
        "protection": "保护",
        "public": "公共",
        "pulse": "脉冲",
        "quality": "质量",
        "query": "查询",
        "radar": "雷达",
        "radiation": "辐射",
        "rate": "率",
        "registration": "配准",
        "regulation": "调节",
        "related": "相关",
        "reporting": "报告",
        "resource": "资源",
        "resolution": "分辨率",
        "response": "响应",
        "right": "权利",
        "robot": "机器人",
        "robotic": "机器人",
        "router": "路由器",
        "safety": "安全",
        "satellite": "卫星",
        "scheduling": "调度",
        "scheme": "方案",
        "science": "科学",
        "search": "搜索",
        "self": "自",
        "semiconductor": "半导体",
        "single": "单",
        "social": "社会",
        "society": "社会",
        "software": "软件",
        "soil": "土壤",
        "solution": "解",
        "source": "源",
        "space": "空间",
        "spatial": "空间",
        "stability": "稳定性",
        "state": "状态",
        "stochastic": "随机",
        "strategy": "策略",
        "structural": "结构",
        "study": "研究",
        "sustainability": "可持续性",
        "switching": "交换",
        "system": "系统",
        "teaching": "教学",
        "test": "测试",
        "testing": "测试",
        "thermal": "热",
        "time": "时间",
        "tracking": "跟踪",
        "transformation": "变换",
        "transistor": "晶体管",
        "transmission": "传输",
        "tree": "树",
        "underwater": "水下",
        "urban": "城市",
        "variable": "变量",
        "vector": "向量",
        "visual": "视觉",
        "water": "水",
        "web": "Web",
        "world": "世界",
        "writing": "写作",
    }
)

RAW_COMPONENTS.update(
    {
        "abstracting": "文摘",
        "accurate": "精确",
        "acquisition": "采集",
        "action": "动作",
        "active": "主动",
        "activated": "活性",
        "activation": "活化",
        "air": "空气",
        "allocation": "分配",
        "appearance": "外观",
        "aperture": "孔径",
        "binary": "二进制",
        "chip": "芯片",
        "conservation": "保护",
        "context": "上下文",
        "contour": "轮廓",
        "diode": "二极管",
        "echo": "回声",
        "emission": "发射",
        "emitting": "发光",
        "fluid": "流体",
        "force": "力",
        "generator": "发生器",
        "holography": "全息",
        "intensity": "强度",
        "medicinal": "药用",
        "multiplexing": "复用",
        "objective": "目标",
        "phenomena": "现象",
        "profile": "剖面",
        "profiler": "剖面仪",
        "reduction": "降维",
        "scattering": "散射",
        "stoke": "斯托克斯",
        "transducer": "换能器",
        "velocity": "速度",
    }
)

RAW_COMPONENTS.update(
    {
        "acid": "酸",
        "assistance": "辅助",
        "ambulatory": "门诊",
        "amino": "氨基",
        "animal": "动物",
        "antibody": "抗体",
        "antigen": "抗原",
        "artificial": "人工",
        "association rule": "关联规则",
        "bacterial": "细菌",
        "bee colony": "蜂群",
        "blood": "血液",
        "blood coagulation": "凝血",
        "body": "体",
        "bone": "骨",
        "bone marrow": "骨髓",
        "care": "护理",
        "calcium": "钙",
        "central": "中枢",
        "central nervous": "中枢神经",
        "central nervous system": "中枢神经系统",
        "chemokine": "趋化因子",
        "child": "儿童",
        "chronic": "慢性",
        "clinical": "临床",
        "clinical laboratory": "临床实验室",
        "cranial nerve": "脑神经",
        "critical care": "重症监护",
        "de noising": "去噪",
        "denoising": "去噪",
        "dental": "牙科",
        "diet": "饮食",
        "drug": "药物",
        "distress": "窘迫",
        "disturbance": "扰动",
        "driver": "驾驶",
        "e commerce": "电子商务",
        "elliptic curve": "椭圆曲线",
        "endothelial growth": "内皮生长",
        "equalization": "均衡化",
        "escherichia coli": "大肠杆菌",
        "evidence based": "循证",
        "excitatory amino": "兴奋性氨基",
        "facility": "设施",
        "few shot": "小样本",
        "gamma": "γ",
        "gene": "基因",
        "genome": "基因组",
        "glucagon like peptide": "胰高血糖素样肽",
        "heart": "心脏",
        "heat shock": "热休克",
        "histogram": "直方图",
        "home": "家庭",
        "hospital": "医院",
        "infarction": "梗死",
        "interleukin": "白细胞介素",
        "ion": "离子",
        "ion channel": "离子通道",
        "ischemic": "缺血性",
        "isotope": "同位素",
        "joint": "关节",
        "k means": "K均值",
        "leukemia": "白血病",
        "least square": "最小二乘",
        "life support": "生命支持",
        "load": "负载",
        "load balancing": "负载均衡",
        "lung": "肺",
        "lymphoblastic": "淋巴母细胞",
        "naive bayes": "朴素贝叶斯",
        "nerve": "神经",
        "nervous": "神经",
        "nucleus": "核",
        "myeloid": "髓系",
        "myocardial": "心肌",
        "parity check": "奇偶校验",
        "patient": "患者",
        "peptide": "肽",
        "peripheral": "外周",
        "peripheral nervous": "外周神经",
        "pregnancy": "妊娠",
        "primary": "初级",
        "psychological": "心理",
        "pulmonary": "肺",
        "quadrature amplitude": "正交幅度",
        "radial basis": "径向基",
        "radioisotope": "放射性同位素",
        "recursive least square": "递归最小二乘",
        "rejection": "抑制",
        "respiratory": "呼吸",
        "rna": "RNA",
        "rough set": "粗糙集",
        "rough sets": "粗糙集",
        "sensing": "感知",
        "skin": "皮肤",
        "sodium": "钠",
        "soft tissue": "软组织",
        "spinal": "脊髓",
        "spinal cord": "脊髓",
        "stroke": "卒中",
        "surgical": "外科",
        "tooth": "牙",
        "tumor necrosis": "肿瘤坏死",
        "two way": "双向",
        "viral": "病毒",
        "vitamin": "维生素",
        "vitamin b": "维生素B",
        "vitamin d": "维生素D",
        "wound": "伤口",
        "wound closure": "伤口闭合",
        "worst case": "最坏情况",
    }
)

RAW_COMPONENTS.update(
    {
        "abnormality": "异常",
        "abbreviation": "缩写",
        "acetate": "乙酸盐",
        "activating": "活化",
        "administration": "管理",
        "adrenal": "肾上腺",
        "adenine": "腺嘌呤",
        "african": "非洲",
        "alkaloid": "生物碱",
        "alpha": "α",
        "anesthesia": "麻醉",
        "artery": "动脉",
        "anti": "抗",
        "bile": "胆汁",
        "biliary": "胆道",
        "bacteriophage": "噬菌体",
        "brain": "脑",
        "cardiac": "心脏",
        "carotid": "颈动脉",
        "cationic": "阳离子",
        "cerebral": "脑",
        "carcinoma": "癌",
        "chromosome": "染色体",
        "complement": "补体",
        "cortex": "皮质",
        "death": "死亡",
        "diagnostic": "诊断",
        "dietary": "膳食",
        "duct": "管",
        "eye": "眼",
        "fetal": "胎儿",
        "fistula": "瘘",
        "fracture": "骨折",
        "fungal": "真菌",
        "hemorrhage": "出血",
        "hepatiti": "肝炎",
        "hepatitis": "肝炎",
        "implant": "植入物",
        "injection": "注射",
        "insulin": "胰岛素",
        "insurance": "保险",
        "integrin": "整合素",
        "intestinal": "肠",
        "keratin": "角蛋白",
        "loss": "丢失",
        "lyase": "裂解酶",
        "mycobacterium": "分枝杆菌",
        "mycoplasma": "支原体",
        "neoplasm": "肿瘤",
        "neuron": "神经元",
        "nucleotide": "核苷酸",
        "nucleu": "核",
        "nursing": "护理",
        "ocular": "眼",
        "oil": "油",
        "oral": "口腔",
        "autoimmune": "自身免疫",
        "neurological": "神经",
        "organ": "器官",
        "oxidase": "氧化酶",
        "people": "人群",
        "personnel": "人员",
        "pharmacy": "药学",
        "phosphate": "磷酸盐",
        "poisoning": "中毒",
        "potassium": "钾",
        "proto oncogene": "原癌基因",
        "procedure": "操作",
        "prosthesi": "假体",
        "prosthesis": "假体",
        "reductase": "还原酶",
        "renal": "肾",
        "retinal": "视网膜",
        "small": "小",
        "streptococcu": "链球菌",
        "sulfate": "硫酸盐",
        "therapeutic": "治疗",
        "tissue": "组织",
        "translocator": "转位酶",
        "transporter": "转运蛋白",
        "typing": "分型",
        "tuberculosi": "结核病",
        "tuberculosis": "结核病",
        "valve": "瓣膜",
        "vein": "静脉",
        "venom": "毒液",
        "veterinary": "兽医",
        "viruse": "病毒",
        "weight": "重量",
        "rehabilitation": "康复",
        "kidney": "肾脏",
        "liver": "肝脏",
        "hypertension": "高血压",
        "polymerase": "聚合酶",
        "sleep": "睡眠",
    }
)

RAW_COMPONENTS.update(
    {
        "abscess": "脓肿",
        "aortic aneurysm": "主动脉瘤",
        "bacteria": "细菌",
        "cavity": "腔",
        "coronary aneurysm": "冠状动脉瘤",
        "coronary artery": "冠状动脉",
        "dioxygenase": "双加氧酶",
        "disability": "残疾",
        "facility": "设施",
        "flow": "流动",
        "hydrochloride": "盐酸盐",
        "implantation": "植入",
        "phosphodiesterase": "磷酸二酯酶",
        "protease": "蛋白酶",
        "scale": "量表",
        "solution": "溶液",
        "stenosis": "狭窄",
        "sulfate": "硫酸盐",
        "thrombosis": "血栓形成",
        "tolerance": "耐受",
        "training": "训练",
        "transaminase": "转氨酶",
        "abuse": "虐待",
        "adenosine": "腺苷",
        "adhesion": "黏附",
        "alcohol": "酒精",
        "american": "美国",
        "anemia": "贫血",
        "aneurysm": "动脉瘤",
        "apolipoprotein": "载脂蛋白",
        "aortic": "主动脉",
        "area": "区域",
        "associated": "相关",
        "base": "碱基",
        "binding site": "结合位点",
        "bovine": "牛",
        "cervical": "颈部",
        "clostridium": "梭菌",
        "collagen": "胶原",
        "congenital": "先天性",
        "coronary": "冠状动脉",
        "cutaneous": "皮肤",
        "cyclic": "环状",
        "cyclin": "细胞周期蛋白",
        "cytochrome": "细胞色素",
        "dehydrogenase": "脱氢酶",
        "denture": "义齿",
        "diphosphate": "二磷酸",
        "dysplasia": "发育不良",
        "encephalitis": "脑炎",
        "epilepsy": "癫痫",
        "exercise": "运动",
        "exposure": "暴露",
        "failure": "衰竭",
        "familial": "家族性",
        "gastric": "胃",
        "genomic": "基因组",
        "glucose": "葡萄糖",
        "group": "群",
        "hearing": "听力",
        "hereditary": "遗传性",
        "herpesvirus": "疱疹病毒",
        "hiv": "HIV",
        "immunoglobulin": "免疫球蛋白",
        "inbred": "近交",
        "induced": "诱导",
        "infectious": "感染性",
        "infant": "婴儿",
        "inhibitor": "抑制剂",
        "institute": "研究所",
        "kinase": "激酶",
        "ligament": "韧带",
        "lymphocyte": "淋巴细胞",
        "lymphoma": "淋巴瘤",
        "mass": "质量",
        "membrane": "膜",
        "metabolic": "代谢",
        "metabolism": "代谢",
        "mice": "小鼠",
        "microscopy": "显微镜",
        "molecule": "分子",
        "movement": "运动",
        "muscle": "肌肉",
        "national": "国家",
        "non": "非",
        "obstruction": "阻塞",
        "oncogene": "癌基因",
        "orthodontic": "正畸",
        "pair": "对",
        "particle": "颗粒",
        "person": "人",
        "pneumonia": "肺炎",
        "potential": "电位",
        "professional": "职业",
        "prostaglandin": "前列腺素",
        "proto": "原",
        "rats": "大鼠",
        "review": "综述",
        "ribonucleoprotein": "核糖核蛋白",
        "sarcoma": "肉瘤",
        "sea": "海",
        "sequence": "序列",
        "sexual": "性",
        "sinus": "窦",
        "site": "位点",
        "size": "大小",
        "stimulation": "刺激",
        "stress": "应激",
        "substance": "物质",
        "sugar": "糖",
        "toxin": "毒素",
        "traumatic": "创伤性",
        "tumor": "肿瘤",
        "united state": "美国",
        "unit": "单元",
        "urinary": "尿",
        "uterine": "子宫",
        "vaccine": "疫苗",
        "ventricular": "心室",
        "virus": "病毒",
        "volume": "体积",
        "x ray": "X射线",
    }
)

RAW_EXACT_ALIASES.update(
    {
        "multiple input multiple output mimo": "多输入多输出",
        "multiple input multiple output mimo radar": "多输入多输出雷达",
        "multiple input multiple output mimo system": "多输入多输出系统",
        "shape memory": "形状记忆",
        "shape memory alloy": "形状记忆合金",
        "shape memory alloy actuator": "形状记忆合金执行器",
        "ac ac converter": "AC-AC转换器",
        "bang bang control": "Bang-Bang控制",
        "biometric identification": "生物识别",
        "biometric recognition": "生物识别",
        "covid 19 clinical research study": "COVID-19临床研究",
        "human human interaction": "人人交互",
        "intelligent agent": "智能体",
        "internet of thing": "物联网",
        "internet of thing iot": "物联网",
        "internet of things": "物联网",
        "internet of things iot": "物联网",
        "linear time temporal logic": "线性时序逻辑",
        "administration oral": "口服给药",
        "airway management": "气道管理",
        "african continental ancestry group": "非洲大陆祖源群体",
        "academic integrity and plagiarism": "学术诚信与剽窃",
        "acetylcholine release inhibitor": "乙酰胆碱释放抑制剂",
        "acetylcholine release inhibitors": "乙酰胆碱释放抑制剂",
        "adaboost algorithm": "AdaBoost算法",
        "adenylosuccinate lyase": "腺苷酸琥珀酸裂解酶",
        "asian continental ancestry group": "亚洲大陆祖源群体",
        "abortifacient agent": "堕胎药",
        "abortifacient agents": "堕胎药",
        "barium radioisotope": "钡放射性同位素",
        "barium radioisotopes": "钡放射性同位素",
        "body composition": "身体成分",
        "body temperature": "体温",
        "brownian motion": "布朗运动",
        "cell division": "细胞分裂",
        "cell nucleus division": "细胞核分裂",
        "clinical trial": "临床试验",
        "clinical trial phase i": "I期临床试验",
        "clinical trial phase ii": "II期临床试验",
        "clinical trial phase iii": "III期临床试验",
        "colored petri net": "有色Petri网",
        "co operative diversity": "协作分集",
        "co operative spectrum sensing": "协作频谱感知",
        "co operative system": "协作系统",
        "cyclic redundancy check": "循环冗余校验",
        "european continental ancestry group": "欧洲大陆祖源群体",
        "fourier series": "傅里叶级数",
        "fracture closed": "闭合性骨折",
        "fractures closed": "闭合性骨折",
        "frequency locked loop": "频率锁定环",
        "11 beta hydroxysteroid dehydrogenase": "11β-羟类固醇脱氢酶",
        "11 beta hydroxysteroid dehydrogenase type 1": "11β-羟类固醇脱氢酶1型",
        "11 beta hydroxysteroid dehydrogenase type 2": "11β-羟类固醇脱氢酶2型",
        "lattice boltzmann method": "格子玻尔兹曼方法",
        "mean shift algorithm": "均值漂移算法",
        "memory address": "内存地址",
        "optimal solution": "最优解",
        "oral administration": "口服给药",
        "oral communication": "口头交流",
        "oral history": "口述史",
        "oral history memory narrative analysis": "口述史记忆叙事分析",
        "organ transplantation": "器官移植",
        "planar monopole antenna": "平面单极子天线",
        "platelet factor 4": "血小板因子4",
        "public administration": "公共行政",
        "public administration and governance": "公共行政与治理",
        "quadratic programming": "二次规划",
        "receptor interleukin 7": "白细胞介素7受体",
        "schur complement": "Schur补",
        "silicon on insulator": "绝缘体上硅",
        "solid phase extraction": "固相萃取",
        "stroke volume": "每搏量",
        "surgery plastic": "整形外科",
        "tooth extraction": "拔牙",
        "viral marketing": "病毒式营销",
        "zero knowledge proof": "零知识证明",
        "accident traffic": "交通事故",
        "air traffic control": "空中交通管制",
        "air traffic controller": "空中交通管制员",
        "air traffic management": "空中交通管理",
        "air traffic management and optimization": "空中交通管理与优化",
        "animal scale": "动物鳞片",
        "antibody viral": "病毒抗体",
        "antigen viral": "病毒抗原",
        "antigen viral tumor": "病毒性肿瘤抗原",
        "anomalous left coronary artery": "左冠状动脉异常",
        "approximate dynamic programming": "近似动态规划",
        "ball grid array": "球栅阵列",
        "bronchiolitis viral": "病毒性细支气管炎",
        "chip scale packaging": "芯片级封装",
        "chromosome artificial human": "人造人类染色体",
        "chromosome human": "人类染色体",
        "chromosome human 13 15": "人类13-15号染色体",
        "chromosome human 16 18": "人类16-18号染色体",
        "computational grid": "计算网格",
        "discharge electric": "放电",
        "electric clock": "电钟",
        "electric control equipment": "电气控制设备",
        "grid based": "基于网格",
        "grid cell": "网格细胞",
        "memory cultural": "文化记忆",
        "cultural memory": "文化记忆",
        "cognitive function and memory": "认知功能与记忆",
        "identity memory and therapy": "身份、记忆与治疗",
        "literature and cultural memory": "文学与文化记忆",
        "active transport cell nucleus": "细胞核主动转运",
        "research study": "研究",
        "research studies": "研究",
        "acoustic echo cancellation": "声学回声消除",
        "agriculture land use rural development": "农业、土地利用与农村发展",
        "all digital phase locked loop": "全数字锁相环",
        "analytic and geometric function theory": "解析与几何函数论",
        "analytic network process": "网络分析法",
        "analytic number theory research": "解析数论研究",
        "animal assisted therapy": "动物辅助治疗",
        "aquatic life and conservation": "水生生物与保护",
        "aquatic therapy": "水疗",
        "architecture verification and validation": "架构验证与确认",
        "authenticated key agreement": "认证密钥协商",
        "authentication and key agreements": "认证与密钥协商",
        "automated guided vehicles": "自动导引车",
        "automatic gain control": "自动增益控制",
        "average link clustering": "平均链路聚类",
        "belief propagation decoding": "置信传播解码",
        "blood gas analysis": "血气分析",
        "business rules": "业务规则",
        "c means": "C均值",
        "cable tv": "有线电视",
        "calcium channel l type": "L型钙通道",
        "calcium channels l type": "L型钙通道",
        "calcium channels n type": "N型钙通道",
        "calcium channels p type": "P型钙通道",
        "calcium channels q type": "Q型钙通道",
        "calcium channels r type": "R型钙通道",
        "calcium channels t type": "T型钙通道",
        "case base": "案例库",
        "case based reasoning": "基于案例的推理",
        "case based reasoning approaches": "基于案例的推理方法",
        "case control studies": "病例对照研究",
        "case representation": "案例表示",
        "cell broadband engine": "Cell宽带引擎",
        "cell cycle": "细胞周期",
        "cell cycle proteins": "细胞周期蛋白",
        "closed loop control": "闭环控制",
        "closed loop control system": "闭环控制系统",
        "closed loop control systems": "闭环控制系统",
        "closed loop signal": "闭环信号",
        "closed loop signals": "闭环信号",
        "closed loop system": "闭环系统",
        "closed loop systems": "闭环系统",
        "closed loop supply chain": "闭环供应链",
        "cluster head node": "簇头节点",
        "cluster head nodes": "簇头节点",
        "collision free path": "无碰撞路径",
        "collision free paths": "无碰撞路径",
        "color quantization": "颜色量化",
        "fuzzy and soft set theory": "模糊与软集理论",
        "full adder": "全加器",
        "hard real time": "硬实时",
        "internet protocol ip": "互联网协议IP",
        "k means": "K均值",
        "mobile rfid": "移动RFID",
        "net zero": "净零",
        "real time": "实时",
    }
)

RAW_PRIORITY_COMPONENTS = {
    "agent": "智能体",
    "agile": "敏捷",
    "ai": "AI",
    "aluminum": "铝",
    "ambient": "环境",
    "antimicrobial": "抗微生物",
    "approach": "方法",
    "aquatic": "水生",
    "astronomy": "天文学",
    "automata": "自动机",
    "automation": "自动化",
    "automotive": "汽车",
    "blind": "盲",
    "biped": "双足",
    "binocular": "双目",
    "broadband": "宽带",
    "broadcast": "广播",
    "broadcasting": "广播",
    "building": "建筑",
    "cable": "电缆",
    "cache": "缓存",
    "cancellation": "消除",
    "carrier": "载波",
    "change": "变化",
    "chromosome": "染色体",
    "classifier": "分类器",
    "clock": "时钟",
    "cluster": "聚类",
    "collaborative": "协同",
    "combustion": "燃烧",
    "complex": "复杂",
    "congestion": "拥塞",
    "contamination": "污染",
    "continuou": "连续",
    "convergence": "收敛",
    "core": "核心",
    "cost": "成本",
    "conversion": "转换",
    "cooperative": "协作",
    "cross": "交叉",
    "current": "电流",
    "cycle": "循环",
    "decoding": "解码",
    "dielectric": "电介质",
    "difference": "差异",
    "diffusion": "扩散",
    "document": "文档",
    "efficiency": "效率",
    "encryption": "加密",
    "ensemble": "集成",
    "ecosystem": "生态系统",
    "ethic": "伦理",
    "evolution": "演化",
    "evolutionary": "进化",
    "fast": "快速",
    "file": "文件",
    "files": "文件",
    "forecasting": "预测",
    "formal": "形式化",
    "framework": "框架",
    "fuel": "燃料",
    "gain": "增益",
    "gains": "增益",
    "gas": "气体",
    "gene": "基因",
    "gender": "性别",
    "gear": "齿轮",
    "gears": "齿轮",
    "geography": "地理",
    "grey": "灰色",
    "green": "绿色",
    "group": "群组",
    "growth": "生长",
    "guided": "导引",
    "hardware": "硬件",
    "heat": "热",
    "heterogeneou": "异构",
    "heterogeneous": "异构",
    "hybrid": "混合",
    "hydraulic": "液压",
    "identification": "识别",
    "infection": "感染",
    "inference": "推理",
    "international": "国际",
    "ip": "IP",
    "kinematic": "运动学",
    "kinematics": "运动学",
    "layer": "层",
    "linguistic": "语言",
    "local": "局部",
    "loop": "环路",
    "loops": "环路",
    "map": "映射",
    "maps": "映射",
    "market": "市场",
    "matching": "匹配",
        "medicine": "医学",
        "mems": "MEMS",
        "metal": "金属",
        "metamaterial": "超材料",
        "metamaterials": "超材料",
        "microscopy": "显微镜",
        "migration": "迁移",
        "military": "军事",
        "mitigation": "缓解",
        "maturity": "成熟度",
        "mobility": "移动性",
        "modeling": "建模",
        "modelling": "建模",
    "multicast": "组播",
    "multimedia": "多媒体",
    "mutation": "突变",
    "nanomaterial": "纳米材料",
    "nanomaterials": "纳米材料",
    "negative": "负",
    "number": "数",
    "numerical": "数值",
    "ocean": "海洋",
    "online": "在线",
    "operation": "操作",
    "organic": "有机",
    "p2p": "P2P",
    "particle": "粒子",
    "perception": "感知",
    "photonic": "光子",
    "pollution": "污染",
    "polymer": "聚合物",
    "probability": "概率",
    "product": "产品",
    "propulsion": "推进",
    "pump": "泵",
    "pumps": "泵",
    "quantization": "量化",
    "radio": "无线电",
    "range": "范围",
    "ratio": "比率",
    "ray": "射线",
    "reaction": "反应",
    "recommendation": "推荐",
    "relay": "中继",
    "relation": "关系",
    "reliability": "可靠性",
    "remote": "遥感",
    "requirement": "需求",
    "resistance": "抗性",
    "rfid": "RFID",
    "ring": "环",
    "rings": "环",
    "risk": "风险",
    "rule": "规则",
    "rules": "规则",
    "sar": "SAR",
    "selection": "选择",
    "sensing": "感知",
    "sequence": "序列",
    "server": "服务器",
    "set": "集",
    "sets": "集",
    "sharing": "共享",
    "task": "任务",
    "tasks": "任务",
    "tcp": "TCP",
    "tool": "工具",
    "tools": "工具",
    "type": "类型",
    "types": "类型",
    "uwb": "UWB",
    "validation": "验证",
    "variational": "变分",
    "view": "视图",
    "views": "视图",
    "walking": "行走",
    "word": "词",
    "words": "词",
    "zero": "零",
    "signaling": "信令",
    "spectral": "频谱",
    "spectroscopy": "光谱学",
    "standard": "标准",
    "stress": "应力",
    "superconducting": "超导",
    "telecommunication": "电信",
    "temperature": "温度",
    "therapy": "治疗",
    "tomography": "断层成像",
    "translation": "翻译",
    "transportation": "运输",
    "value": "值",
    "verification": "验证",
    "voltage": "电压",
    "waste": "废弃物",
    "adaptation": "适应",
    "african": "非洲",
    "aircraft": "飞机",
    "america": "美洲",
    "american": "美国",
    "analog": "模拟",
    "anomaly": "异常",
    "arithmetic": "算术",
    "archaeology": "考古学",
    "architectural": "建筑",
    "asian": "亚洲",
    "assembly": "装配",
    "assignment": "分配",
    "attribute": "属性",
    "automated": "自动化",
    "background": "背景",
    "bandwidth": "带宽",
    "biometric": "生物识别",
    "block": "块",
    "broadcasting": "广播",
    "capacity": "容量",
    "cardiac": "心脏",
    "cardiovascular": "心血管",
    "character": "字符",
    "characterization": "表征",
    "checking": "检查",
    "child": "儿童",
    "clinical": "临床",
    "closed": "闭环",
    "collision": "碰撞",
    "community": "社区",
    "computation": "计算",
    "concept": "概念",
    "constraint": "约束",
    "construction": "构建",
    "consumer": "消费者",
    "consumption": "消费",
    "correlation": "相关",
    "corporate": "企业",
    "coupling": "耦合",
    "covid": "COVID",
    "critical": "临界",
    "crystal": "晶体",
    "customer": "客户",
    "cutting": "切削",
    "cyber": "网络",
    "density": "密度",
    "delivery": "递送",
    "demand": "需求",
    "description": "描述",
    "diagnostic": "诊断",
    "diagram": "图",
    "dimensional": "维",
    "disability": "残疾",
    "discharge": "放电",
    "discovery": "发现",
    "distortion": "失真",
    "distance": "距离",
    "division": "分复用",
    "economy": "经济",
    "efficient": "高效",
    "electrostatic": "静电",
    "element": "元件",
    "embedded": "嵌入式",
    "epidemiology": "流行病学",
    "european": "欧洲",
    "evolutionary": "进化",
    "exchange": "交换",
    "execution": "执行",
    "expression": "表达",
    "extraction": "提取",
    "facial": "面部",
    "fading": "衰落",
    "failure": "故障",
    "family": "家庭",
    "flexible": "柔性",
    "forensic": "取证",
    "formation": "形成",
    "forward": "前向",
    "fourier": "傅里叶",
    "functional": "泛函",
    "gallium": "镓",
    "grating": "光栅",
    "ground": "地面",
    "handling": "处理",
    "inequality": "不等式",
    "influence": "影响",
    "infrared": "红外",
    "infrastructure": "基础设施",
    "injury": "损伤",
    "insect": "昆虫",
    "instrument": "仪器",
    "insulation": "绝缘",
    "integral": "积分",
    "interactive": "交互",
    "inverse": "逆",
    "iterative": "迭代",
    "large": "大规模",
    "leadership": "领导力",
    "liquid": "液体",
    "literary": "文学",
    "location": "定位",
    "lyapunov": "李雅普诺夫",
    "maintenance": "维护",
    "manipulator": "机械臂",
    "matrice": "矩阵",
    "maximum": "最大",
    "mechanic": "力学",
    "mental": "心理",
    "methodology": "方法论",
    "micro": "微",
    "microbial": "微生物",
    "modulator": "调制器",
    "music": "音乐",
    "networking": "网络",
    "neuroscience": "神经科学",
    "nutrition": "营养",
    "order": "阶",
    "oriented": "面向",
    "oscillator": "振荡器",
    "oxide": "氧化物",
    "packaging": "封装",
    "pareto": "帕累托",
    "passive": "无源",
    "pathology": "病理",
    "pedagogy": "教育学",
    "personal": "个人",
    "pharmaceutical": "制药",
    "philosophical": "哲学",
    "physiology": "生理学",
    "piezoelectric": "压电",
    "plastic": "塑料",
    "platform": "平台",
    "polynomial": "多项式",
    "pressure": "压力",
    "processor": "处理器",
    "recording": "记录",
    "reconfigurable": "可重构",
    "recovery": "恢复",
    "reference": "参考",
    "reform": "改革",
    "region": "区域",
    "reproductive": "生殖",
    "resonance": "共振",
    "reasoning": "推理",
    "receiver": "接收机",
    "separation": "分离",
    "sequential": "顺序",
    "shift": "移位",
    "signature": "签名",
    "socioeconomic": "社会经济",
    "sociology": "社会学",
    "solar": "太阳能",
    "solid": "固体",
    "sonar": "声呐",
    "sound": "声音",
    "specy": "物种",
    "speed": "速度",
    "spline": "样条",
    "square": "平方",
    "statistic": "统计",
    "stereo": "立体",
    "stream": "流",
    "streaming": "流媒体",
    "supply": "供应",
    "surveillance": "监测",
    "sustainable": "可持续",
    "swarm": "群",
    "switch": "交换机",
    "synchronization": "同步",
    "synthetic": "合成",
    "taxonomy": "分类学",
    "technical": "技术",
    "television": "电视",
    "temporal": "时间",
    "textile": "纺织",
    "timing": "时序",
    "transition": "跃迁",
    "transformer": "变压器",
    "tumor": "肿瘤",
    "tuning": "调谐",
    "ultrasonic": "超声",
    "vibration": "振动",
    "voice": "语音",
    "watermarking": "水印",
    "wavelength": "波长",
    "wearable": "可穿戴",
    "animal": "动物",
    "application": "应用",
    "representation": "表示",
    "mapping": "映射",
    "approximation": "近似",
    "set": "集合",
    "metabolism": "代谢",
    "message": "消息",
    "outcome": "结果",
    "training": "训练",
    "sport": "体育",
    "implementation": "实现",
    "partial": "部分",
    "support": "支持",
    "class": "类",
    "complexity": "复杂性",
    "artificial": "人工",
    "challenge": "挑战",
    "enhancement": "增强",
    "static": "静态",
    "brain": "脑",
    "prediction": "预测",
    "trade": "贸易",
    "impedance": "阻抗",
    "chaotic": "混沌",
    "segmentation": "分割",
    "scale": "尺度",
    "induced": "诱导",
    "output": "输出",
    "thermodynamic": "热力学",
    "catalysi": "催化",
    "experience": "经验",
    "waveguide": "波导",
    "immune": "免疫",
    "aspect": "方面",
    "atmospheric": "大气",
    "composition": "组成",
    "speaker": "说话人",
    "emotion": "情绪",
    "behavioral": "行为",
    "biochemical": "生化",
    "joint": "关节",
    "finance": "金融",
    "electricity": "电力",
    "concrete": "混凝土",
    "conflict": "冲突",
    "contact": "接触",
    "threshold": "阈值",
    "moving": "运动",
    "switched": "切换",
    "earth": "地球",
    "student": "学生",
    "second": "第二",
    "patient": "患者",
    "programmable": "可编程",
    "fingerprint": "指纹",
    "kernel": "核",
    "geophysical": "地球物理",
    "glass": "玻璃",
    "usability": "可用性",
    "innovative": "创新",
    "input": "输入",
    "religion": "宗教",
    "microstrip": "微带",
    "probabilistic": "概率",
    "syndrome": "综合征",
    "topic": "主题",
    "hierarchical": "层次",
    "rural": "农村",
    "resilience": "韧性",
        "toxicity": "毒性",
        "regional": "区域",
        "medieval": "中世纪",
    "reality": "现实",
    "indigenou": "原住民",
    "bacterial": "细菌",
    "station": "站",
    "decomposition": "分解",
    "volume": "体积",
    "capital": "资本",
    "investment": "投资",
    "factorization": "分解",
    "variation": "变异",
    "polarization": "极化",
    "enterprise": "企业",
    "common": "通用",
    "tourism": "旅游",
    "torque": "转矩",
    "window": "窗口",
    "damage": "损伤",
    "embedding": "嵌入",
    "exploration": "探索",
    "diffraction": "衍射",
    "event": "事件",
    "modern": "现代",
    "vegetation": "植被",
    "labor": "劳动",
    "handover": "切换",
    "frame": "帧",
    "relational": "关系",
    "indoor": "室内",
    "inertial": "惯性",
    "inorganic": "无机",
    "occupational": "职业",
    "photovoltaic": "光伏",
    "secret": "秘密",
    "sparse": "稀疏",
}

RAW_SINGLE_COMPONENT_ALIAS_KEYS = {
        "abrasive",
        "absorption",
        "accelerometer",
        "acoustic",
        "aging",
        "algebra",
        "algorithm",
        "amplifier",
        "antenna",
        "array",
        "audio",
        "authentication",
        "battery",
        "bayesian",
        "beam",
        "biosensor",
        "cellular",
        "circuit",
        "compound",
        "computer",
        "converter",
        "detector",
        "display",
        "dynamics",
        "electromagnetic",
        "electron",
        "energy",
        "engine",
        "equation",
        "estimation",
        "feedback",
        "film",
        "filter",
        "filtering",
        "frequency",
        "gaussian",
        "geometry",
        "graphics",
        "imaging",
        "index",
        "indexing",
        "interference",
        "internet",
        "laser",
        "logic",
        "logistics",
        "machining",
        "magnet",
        "manufacturing",
        "material",
        "mathematics",
        "measurement",
        "memory",
        "metasurface",
        "microcontroller",
        "microwave",
        "modeling",
        "modulation",
        "monitoring",
        "motor",
        "navigation",
        "noise",
        "optics",
        "optimization",
        "particle",
        "physics",
        "power",
        "protein",
        "protocol",
        "quantum",
        "radar",
        "recognition",
        "reconstruction",
        "resonator",
        "robotics",
        "routing",
        "scanning",
        "security",
        "sensor",
        "signal",
        "silicon",
        "simulation",
        "spectrum",
        "surface",
        "synthesis",
        "topology",
        "transistor",
        "transform",
        "video",
        "wave",
        "wavelet",
        "wireless",
}


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _singular_token(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith(("ches", "shes", "sses", "xes", "zes")):
        return token[:-2]
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _key(value: str) -> str:
    text = _clean_text(value).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[\-_/]+", " ", text)
    text = re.sub(r"[^a-z0-9+\s]+", " ", text)
    tokens = [_singular_token(token) for token in text.split() if token]
    return " ".join(tokens)


EXACT_ALIASES = {_key(key): value for key, value in RAW_EXACT_ALIASES.items()}
COMPONENTS = {_key(key): value for key, value in RAW_COMPONENTS.items()}
PRIORITY_COMPONENTS = {**COMPONENTS, **{_key(key): value for key, value in RAW_PRIORITY_COMPONENTS.items()}}
SINGLE_COMPONENT_ALIAS_KEYS = {_key(key) for key in RAW_SINGLE_COMPONENT_ALIAS_KEYS}
NORMALIZED_SUFFIX_PATTERNS = [(_key(key), value) for key, value in SUFFIX_PATTERNS]

MIXED_CLASS_SUFFIXES = {
    "acid": "酸",
    "agonist": "激动剂",
    "analysis": "分析",
    "analysi": "分析",
    "antagonist": "拮抗剂",
    "antigen": "抗原",
    "agent": "药剂",
    "application": "应用",
    "artery": "动脉",
    "assay": "测定",
    "behavior": "行为",
    "bone": "骨",
    "cancer": "癌症",
    "care": "护理",
    "cell": "细胞",
    "chain": "链",
    "channel": "通道",
    "chemical": "化学性",
    "chloride": "氯化物",
    "complex": "复合物",
    "compound": "化合物",
    "center": "中心",
    "control": "控制",
    "cyst": "囊肿",
    "deficiency": "缺乏症",
    "dehydrogenase": "脱氢酶",
    "development": "发展",
    "device": "设备",
    "disease": "疾病",
    "disorder": "障碍",
    "disability": "残疾",
    "domain": "域",
    "dynamic": "动力学",
    "dynamics": "动力学",
    "education": "教育",
    "effect": "效应",
    "element": "元素",
    "enzyme": "酶",
    "factor": "因子",
    "family": "家族",
    "fever": "发热",
    "fluid": "液体",
    "fracture": "骨折",
    "form": "形式",
    "gene": "基因",
    "gland": "腺",
    "group": "群组",
    "health": "健康",
    "history": "历史",
    "hormone": "激素",
    "hospital": "医院",
    "hydrolase": "水解酶",
    "hydroxylase": "羟化酶",
    "imaging": "成像",
    "infection": "感染",
    "inhibitor": "抑制剂",
    "injury": "损伤",
    "isotope": "同位素",
    "kinase": "激酶",
    "ligase": "连接酶",
    "lyase": "裂解酶",
    "management": "管理",
    "material": "材料",
    "medicine": "医学",
    "membrane": "膜",
    "methyltransferase": "甲基转移酶",
    "method": "方法",
    "microscopy": "显微镜",
    "model": "模型",
    "muscle": "肌肉",
    "neoplasm": "肿瘤",
    "nerve": "神经",
    "network": "网络",
    "nursing": "护理",
    "oxide": "氧化物",
    "pain": "疼痛",
    "pathway": "通路",
    "peptide": "肽",
    "perception": "感知",
    "phenomena": "现象",
    "phenomenon": "现象",
    "phosphatase": "磷酸酶",
    "practice": "实践",
    "pressure": "压力",
    "process": "过程",
    "product": "产品",
    "protein": "蛋白",
    "psychology": "心理学",
    "reaction": "反应",
    "receptor": "受体",
    "reductase": "还原酶",
    "region": "区域",
    "relation": "关系",
    "resistance": "抗性",
    "response": "响应",
    "research": "研究",
    "rna": "RNA",
    "science": "科学",
    "service": "服务",
    "structure": "结构",
    "study": "研究",
    "subunit": "亚基",
    "subtype": "亚型",
    "surgery": "手术",
    "syndrome": "综合征",
    "synthase": "合酶",
    "system": "系统",
    "technique": "技术",
    "technology": "技术",
    "test": "测试",
    "testing": "测试",
    "theory": "理论",
    "therapy": "治疗",
    "tissue": "组织",
    "topic": "主题",
    "transplantation": "移植",
    "translocator": "转位酶",
    "transporter": "转运蛋白",
    "treatment": "治疗",
    "tree": "树",
    "tumor": "肿瘤",
    "vaccine": "疫苗",
    "virus": "病毒",
    "viru": "病毒",
    "viral": "病毒性",
    "bacterial": "细菌性",
    "metalloproteinase": "金属蛋白酶",
    "genetic": "遗传",
    "psychological": "心理",
    "dental": "牙科",
    "medical": "医学",
    "experimental": "实验性",
    "organization": "组织",
    "motif": "基序",
    "interaction": "相互作用",
    "acetyltransferase": "乙酰转移酶",
    "acyltransferase": "酰基转移酶",
    "transferase": "转移酶",
    "combination": "组合",
    "radioisotope": "放射性同位素",
    "people": "人群",
    "plant": "植物",
    "procedure": "操作",
    "poisoning": "中毒",
    "oil": "油",
    "joint": "关节",
    "body": "体",
}

AGENT_INTELLIGENT_DOMAINS = {
    "communications_technology",
    "computational_and_artificial_intelligence",
    "computer_science",
    "computers_and_information_processing",
    "robotics_and_automation",
    "systems_engineering_and_theory",
    "systems_man_and_cybernetics",
}

AGENT_DRUG_DOMAINS = {
    "biomedical",
    "chemicals_and_drugs",
    "chemistry",
    "health_sciences",
    "medicine",
    "pharmacology_toxicology_and_pharmaceutics",
    "physical_sciences",
}

ELECTRICAL_CHARGE_DOMAINS = {
    "circuits_and_systems",
    "communications_technology",
    "components_packaging_and_manufacturing_technology",
    "dielectrics_and_electrical_insulation",
    "electron_devices",
    "electromagnetics",
    "engineering",
    "power_electronics",
    "power_engineering_and_energy",
    "signal_processing",
}

GRID_COMPUTING_DOMAINS = AGENT_INTELLIGENT_DOMAINS | {
    "computer_science",
    "computers_and_information_processing",
}

COGNITIVE_MEMORY_DOMAINS = {
    "anthropology_education_sociology_and_social_phenomena",
    "arts_and_humanities",
    "psychology",
    "social_sciences",
}


def _components_for_domains(*, source_priority: bool, domains: Iterable[str]) -> dict[str, str]:
    components = PRIORITY_COMPONENTS if source_priority else COMPONENTS
    domain_set = {str(domain) for domain in domains if str(domain or "")}
    adjusted = dict(components)
    if domain_set & GRID_COMPUTING_DOMAINS:
        adjusted["grid"] = "网格"
        adjusted["traffic"] = "流量"
    if domain_set & ELECTRICAL_CHARGE_DOMAINS:
        adjusted["charge"] = "电荷"
        adjusted["charges"] = "电荷"
    if domain_set & COGNITIVE_MEMORY_DOMAINS:
        adjusted["function"] = "功能"
        adjusted["functions"] = "功能"
        adjusted["memory"] = "记忆"
    if domain_set & AGENT_INTELLIGENT_DOMAINS:
        return adjusted
    if "agent" not in components:
        return adjusted
    if domain_set & AGENT_DRUG_DOMAINS:
        adjusted["agent"] = "药剂"
        adjusted["complex"] = "复合物"
        adjusted["matrix"] = "基质"
        adjusted["scale"] = "量表"
    else:
        adjusted.pop("agent", None)
    return adjusted


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in materialized:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(materialized)


def _candidate_files(candidate_dir: Path) -> list[Path]:
    manifest_path = candidate_dir / "zh_alias_candidate_manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        files: list[Path] = []
        for item in payload.get("batches") or []:
            if not isinstance(item, dict) or not item.get("output"):
                continue
            raw = Path(str(item["output"]))
            if raw.is_absolute():
                files.append(raw)
            elif raw.exists():
                files.append(raw)
            else:
                files.append(candidate_dir / raw.name)
        return sorted(files)
    return sorted(candidate_dir.glob("zh_alias_candidates.batch-*.jsonl"))


def _priority_source(row: dict[str, Any]) -> bool:
    for ref in row.get("source_refs") or []:
        if isinstance(ref, dict) and str(ref.get("source") or "") in PRIORITY_SOURCES:
            return True
    return False


def _is_biomedical_row(row: dict[str, Any]) -> bool:
    return any(str(domain) == "biomedical" for domain in (row.get("domains") or []))


def _is_technical_priority_row(row: dict[str, Any]) -> bool:
    domains = {str(domain) for domain in (row.get("domains") or []) if str(domain or "")}
    return bool(domains & TECHNICAL_PRIORITY_DOMAINS)


def _generated_candidates(row: dict[str, Any]) -> bool:
    candidates = row.get("zh_alias_candidates") or []
    if not candidates:
        return False
    return all(
        isinstance(candidate, dict) and str(candidate.get("source") or "").startswith("agent_")
        for candidate in candidates
    )


def _english_terms(row: dict[str, Any]) -> list[tuple[str, bool]]:
    canonical = str(row.get("canonical_en") or "")
    aliases = [str(alias) for alias in (row.get("aliases_en") or [])]
    terms = [canonical]
    terms.extend(aliases)
    if not _priority_source(row) and "," in canonical:
        non_inverted_aliases = [alias for alias in aliases if "," not in alias]
        terms = [*non_inverted_aliases, canonical, *aliases]
    out: list[str] = []
    seen: set[str] = set()
    for term in terms:
        clean = _clean_text(term)
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            out.append((clean, clean.casefold() == canonical.casefold()))
    return out


def _uninvert_mesh_label(key: str) -> str:
    if "," not in key:
        return key
    parts = [part.strip() for part in key.split(",") if part.strip()]
    if len(parts) < 2:
        return key
    head, modifiers = parts[0], parts[1:]
    return " ".join([*modifiers, head])


def _original_token_forms(value: str) -> dict[str, str]:
    text = _clean_text(value)
    text = text.replace("&", " and ")
    text = re.sub(r"[\-_/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9+\s]+", " ", text)
    forms: dict[str, str] = {}
    for raw_token in text.split():
        normalized = _key(raw_token)
        if normalized and normalized not in forms:
            forms[normalized] = raw_token
    return forms


def _looks_like_source_acronym(original_token: str | None) -> bool:
    if not original_token:
        return False
    letters = re.sub(r"[^A-Za-z]+", "", original_token)
    return bool(letters) and letters.upper() == letters and any(char.isupper() for char in original_token)


def _render_unknown_english_token(token: str, original_token: str | None) -> str:
    if _looks_like_source_acronym(original_token):
        return token.upper()
    if original_token and re.fullmatch(r"[A-Za-z][A-Za-z0-9+]*", original_token):
        return original_token[0].upper() + original_token[1:].lower()
    return token.capitalize()


def _priority_token_fallback(
    token: str,
    *,
    allow_english_unknown: bool = False,
    original_token: str | None = None,
) -> str | None:
    if token in {"as", "by", "for", "from", "into", "of", "on", "to", "with"}:
        return None
    if token.isdigit():
        return token
    if re.fullmatch(r"[a-z]+\d+|\d+[a-z]+", token):
        return token.upper()
    if (
        1 <= len(token) <= 4
        and token not in {"high", "into", "low", "new", "old", "over", "set", "under"}
        and _looks_like_source_acronym(original_token)
    ):
        return token.upper()
    if allow_english_unknown and re.fullmatch(r"[a-z][a-z0-9]*", token):
        return _render_unknown_english_token(token, original_token)
    return None


def _redundant_adjacent_translation(left: str, right: str) -> bool:
    left = _clean_text(left)
    right = _clean_text(right)
    if not left or not right:
        return False
    if left == right:
        return True
    return len(left) >= 2 and len(right) >= 2 and (left.startswith(right) or right.startswith(left))


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _ascii_alias_part(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9 .+\-]+", value)) and not _contains_cjk(value)


def _starts_ascii_alias_part(value: str) -> bool:
    return bool(value) and bool(re.match(r"[A-Za-z0-9]", value))


def _ends_ascii_alias_part(value: str) -> bool:
    return bool(value) and bool(re.search(r"[A-Za-z0-9]$", value))


def _non_acronym_ascii_segment_count(value: str) -> int:
    count = 0
    for segment in re.findall(r"[A-Za-z][A-Za-z0-9]*", value):
        if segment.isupper() and len(segment) <= 8:
            continue
        count += 1
    return count


def _short_single_source_label(value: str) -> bool:
    text = _clean_text(value)
    if " " in text:
        return False
    compact = re.sub(r"[^A-Za-z0-9]+", "", text)
    return bool(compact) and len(compact) <= 5


SOURCE_LABEL_STOPWORDS = {
    "A",
    "An",
    "And",
    "As",
    "At",
    "By",
    "For",
    "From",
    "In",
    "Into",
    "Of",
    "On",
    "Or",
    "The",
    "To",
    "With",
}


def _source_label_display(value: str) -> str:
    parts = _clean_text(value).split()
    rendered: list[str] = []
    for index, part in enumerate(parts):
        if index > 0 and part in SOURCE_LABEL_STOPWORDS:
            rendered.append(part.lower())
        else:
            rendered.append(part)
    return " ".join(rendered)


def _render_mixed_prefix_token(
    token: str,
    components: dict[str, str],
    *,
    original_token: str | None = None,
) -> str | None:
    if token in {"a", "an", "the"}:
        return None
    if token in components:
        return components[token]
    if token.isdigit():
        return token
    if re.fullmatch(r"[a-z]+\d+|\d+[a-z]+", token):
        return token.upper()
    if 1 <= len(token) <= 4:
        return _render_unknown_english_token(token, original_token)
    return _render_unknown_english_token(token, original_token)


def _join_mixed_alias_parts(parts: list[str], suffix: str) -> str | None:
    out = ""
    previous = ""
    previous_ends_ascii = False
    for part in parts:
        if not part:
            continue
        if previous and _redundant_adjacent_translation(previous, part):
            return None
        if out and previous_ends_ascii and _starts_ascii_alias_part(part):
            out += " "
        out += part
        previous = part
        previous_ends_ascii = _ends_ascii_alias_part(part)
    if not out or (previous and _redundant_adjacent_translation(previous, suffix)):
        return None
    if previous_ends_ascii and _starts_ascii_alias_part(suffix):
        return f"{out} {suffix}"
    return f"{out}{suffix}"


def _join_translated_component_parts(parts: list[str]) -> str:
    out = ""
    previous_ends_ascii = False
    for part in parts:
        if out and previous_ends_ascii and _starts_ascii_alias_part(part):
            out += " "
        out += part
        previous_ends_ascii = _ends_ascii_alias_part(part)
    return out


def _mixed_class_suffix_alias(
    key: str,
    *,
    components: dict[str, str],
    original_tokens: dict[str, str] | None = None,
    max_prefix_tokens: int = 4,
    allow_and_token: bool = False,
) -> str | None:
    original_tokens = original_tokens or {}
    tokens = [token for token in _uninvert_mesh_label(key).split() if token]
    if not tokens:
        return None
    cleaned_tokens: list[str] = []
    for token in tokens:
        if token == "s" and cleaned_tokens:
            continue
        cleaned_tokens.append(token)
    tokens = cleaned_tokens
    relation_tokens = {"and", "or", "of", "in", "for", "with", "by", "on", "to", "from", "into", "between"}
    for token in tokens:
        if token not in relation_tokens:
            continue
        if not allow_and_token or token != "and":
            return None
    for size in range(min(3, len(tokens)), 0, -1):
        suffix_key = " ".join(tokens[-size:])
        suffix = MIXED_CLASS_SUFFIXES.get(suffix_key)
        if not suffix:
            continue
        prefix_tokens = tokens[:-size]
        if not prefix_tokens or len(prefix_tokens) > max_prefix_tokens:
            return None
        prefix_parts: list[str] = []
        if all(token.isdigit() for token in prefix_tokens):
            prefix_parts.append("-".join(prefix_tokens))
        else:
            for token in prefix_tokens:
                if allow_and_token and token == "and":
                    part = "与"
                    prefix_parts.append(part)
                    continue
                if suffix_key == "artery" and token == "coronary":
                    prefix_parts.append("冠状")
                    continue
                part = _render_mixed_prefix_token(token, components, original_token=original_tokens.get(token))
                if not part:
                    return None
                prefix_parts.append(part)
        return _join_mixed_alias_parts(prefix_parts, suffix)
    return None


GTP_BINDING_SUFFIX_ALIASES = [
    ("gtp binding protein alpha subunit", "GTP结合蛋白α亚基"),
    ("gtp binding protein beta subunit", "GTP结合蛋白β亚基"),
    ("gtp binding protein gamma subunit", "GTP结合蛋白γ亚基"),
    ("gtp binding protein", "GTP结合蛋白"),
]

GTP_BINDING_PREFIX_ALIASES = {
    "heterotrimeric": "异源三聚体",
    "monomeric": "单体",
}


def _biomolecular_gtp_binding_alias(
    key: str,
    *,
    components: dict[str, str],
    original_tokens: dict[str, str],
) -> str | None:
    for suffix_key, suffix_zh in GTP_BINDING_SUFFIX_ALIASES:
        if key == suffix_key:
            return suffix_zh
        if not key.endswith(f" {suffix_key}"):
            continue
        prefix = key[: -(len(suffix_key) + 1)].strip()
        if not prefix:
            return suffix_zh
        prefix_tokens = prefix.split()
        if len(prefix_tokens) > 3:
            return None
        prefix_parts: list[str] = []
        for token in prefix_tokens:
            part = GTP_BINDING_PREFIX_ALIASES.get(token)
            if not part:
                part = _render_mixed_prefix_token(token, components, original_token=original_tokens.get(token))
            if not part:
                return None
            prefix_parts.append(part)
        return _join_mixed_alias_parts(prefix_parts, suffix_zh)
    return None


def _cytochrome_p450_alias(key: str) -> str | None:
    match = re.fullmatch(r"cytochrome p 450 (cyp[0-9a-z]+) inhibitor", key)
    if match:
        return f"细胞色素P450 {match.group(1).upper()}抑制剂"
    if key == "cytochrome p 450 enzyme inhibitor":
        return "细胞色素P450酶抑制剂"
    return None


def _chromosome_human_pair_alias(key: str) -> str | None:
    match = re.fullmatch(r"chromosome human pair ([0-9]+|x|y)", key)
    if not match:
        return None
    marker = match.group(1).upper()
    return f"人类{marker}号染色体"


def _influenza_virus_alias(key: str) -> str | None:
    match = re.fullmatch(r"influenza ([abc]) viru", key)
    if not match:
        return None
    subtype = {"a": "甲型", "b": "乙型", "c": "丙型"}[match.group(1)]
    return f"{subtype}流感病毒"


def _proto_oncogene_protein_alias(key: str) -> str | None:
    if not key.startswith("proto oncogene protein "):
        return None
    tail = key[len("proto oncogene protein ") :].strip()
    if not tail:
        return None
    label = "-".join(part.upper() for part in tail.split())
    return f"原癌基因蛋白{label}"


MARKER_ALIASES = {
    "i": "I",
    "ii": "II",
    "iii": "III",
    "iv": "IV",
    "v": "V",
    "vi": "VI",
    "vii": "VII",
    "viii": "VIII",
    "ix": "IX",
    "x": "X",
}


def _biomedical_marker_alias(token: str) -> str | None:
    if token.isdigit():
        return token
    if token in MARKER_ALIASES:
        return MARKER_ALIASES[token]
    if re.fullmatch(r"[a-z]", token) and token not in {"a", "i"}:
        return token.upper()
    return None


def _biomedical_numbered_entity_alias(
    key: str,
    *,
    components: dict[str, str],
    original_tokens: dict[str, str],
) -> str | None:
    tokens = key.split()
    if len(tokens) < 3:
        return None
    marker = _biomedical_marker_alias(tokens[-1])
    if not marker:
        return None
    if tokens[-2] == "type" and len(tokens) >= 4:
        base_key = " ".join(tokens[:-2])
        base_alias = _mixed_class_suffix_alias(base_key, components=components, original_tokens=original_tokens)
        if not base_alias:
            base_alias = _translate_component_phrase(
                base_key,
                components=components,
                original_tokens=original_tokens,
                source_priority=False,
                allow_english_unknown=True,
            )
        if base_alias:
            return f"{base_alias}{marker}型"
        return None
    base_key = " ".join(tokens[:-1])
    base_alias = _mixed_class_suffix_alias(base_key, components=components, original_tokens=original_tokens)
    if base_alias:
        return f"{base_alias}{marker}"
    return None


def _as_topic_alias(
    key: str,
    *,
    components: dict[str, str],
    original_tokens: dict[str, str],
) -> str | None:
    if not key.endswith(" as topic"):
        return None
    base_key = key[: -len(" as topic")].strip()
    if not base_key:
        return None
    phase_match = re.fullmatch(r"clinical trial phase ([ivx]+|\d+)", base_key)
    if phase_match:
        marker = _biomedical_marker_alias(phase_match.group(1)) or phase_match.group(1).upper()
        return f"{marker}期临床试验主题"
    base_alias = _translate_component_phrase(
        base_key,
        components=components,
        original_tokens=original_tokens,
        source_priority=False,
        allow_english_unknown=False,
    )
    if not base_alias:
        base_alias = _mixed_class_suffix_alias(base_key, components=components, original_tokens=original_tokens)
    if not base_alias:
        return None
    return f"{base_alias}主题"


def _translate_component_phrase(
    key: str,
    *,
    components: dict[str, str] | None = None,
    original_tokens: dict[str, str] | None = None,
    source_priority: bool = False,
    allow_english_unknown: bool = False,
) -> str | None:
    components = components or COMPONENTS
    original_tokens = original_tokens or {}
    key = _uninvert_mesh_label(key)
    key = re.sub(r"^(?:a|an|the)\s+", "", key).strip()
    key = re.sub(r"\s+(?:and)$", "", key).strip()
    if key in EXACT_ALIASES:
        return EXACT_ALIASES[key]
    if key in components:
        return components[key]
    tokens = key.split()
    if not tokens:
        return None
    if tokens[0] == "non" and len(tokens) > 1:
        rest_zh = _translate_component_phrase(
            " ".join(tokens[1:]),
            components=components,
            original_tokens=original_tokens,
            source_priority=source_priority,
            allow_english_unknown=allow_english_unknown,
        )
        if rest_zh:
            return f"非{rest_zh}"
    if "based" in tokens:
        based_index = tokens.index("based")
        left = " ".join(tokens[:based_index])
        right = " ".join(tokens[based_index + 1 :])
        left_zh = _translate_component_phrase(
            left,
            components=components,
            original_tokens=original_tokens,
            source_priority=source_priority,
            allow_english_unknown=allow_english_unknown,
        ) if left else None
        right_zh = _translate_component_phrase(
            right,
            components=components,
            original_tokens=original_tokens,
            source_priority=source_priority,
            allow_english_unknown=allow_english_unknown,
        ) if right else None
        if left_zh and right_zh:
            if _redundant_adjacent_translation(left_zh, right_zh):
                return None
            return f"基于{left_zh}的{right_zh}"
        if left_zh and not right:
            return f"基于{left_zh}"
    if source_priority:
        relation_templates = {
            "for": lambda left_zh, right_zh: f"用于{right_zh}的{left_zh}",
            "with": lambda left_zh, right_zh: f"带{right_zh}的{left_zh}",
            "by": lambda left_zh, right_zh: f"基于{right_zh}的{left_zh}",
            "on": lambda left_zh, right_zh: f"{right_zh}上的{left_zh}",
            "to": lambda left_zh, right_zh: f"{left_zh}到{right_zh}",
        }
        for relation, template in relation_templates.items():
            if relation not in tokens:
                continue
            relation_index = tokens.index(relation)
            left = " ".join(tokens[:relation_index])
            right = " ".join(tokens[relation_index + 1 :])
            if not left or not right:
                continue
            left_zh = _translate_component_phrase(
                left,
                components=components,
                original_tokens=original_tokens,
                source_priority=source_priority,
                allow_english_unknown=allow_english_unknown,
            )
            right_zh = _translate_component_phrase(
                right,
                components=components,
                original_tokens=original_tokens,
                source_priority=source_priority,
                allow_english_unknown=allow_english_unknown,
            )
            if left_zh and right_zh:
                if _redundant_adjacent_translation(left_zh, right_zh):
                    return None
                return template(left_zh, right_zh)
    if "and" in tokens:
        parts = [part.strip() for part in key.split(" and ") if part.strip()]
        if len(parts) >= 2:
            translated = [
                _translate_component_phrase(
                    part,
                    components=components,
                    original_tokens=original_tokens,
                    source_priority=source_priority,
                    allow_english_unknown=allow_english_unknown,
                )
                for part in parts
            ]
            if all(translated):
                for previous, current in zip(translated, translated[1:]):
                    if _redundant_adjacent_translation(str(previous), str(current)):
                        return None
                return "与".join(str(item) for item in translated)
    if "in" in tokens:
        left, sep, right = key.partition(" in ")
        if sep:
            left_zh = _translate_component_phrase(
                left,
                components=components,
                original_tokens=original_tokens,
                source_priority=source_priority,
                allow_english_unknown=allow_english_unknown,
            )
            right_zh = _translate_component_phrase(
                right,
                components=components,
                original_tokens=original_tokens,
                source_priority=source_priority,
                allow_english_unknown=allow_english_unknown,
            )
            if left_zh and right_zh:
                if _redundant_adjacent_translation(left_zh, right_zh):
                    return None
                return f"{right_zh}中的{left_zh}"
    if "of" in tokens:
        left, sep, right = key.partition(" of ")
        if sep:
            left_zh = _translate_component_phrase(
                left,
                components=components,
                original_tokens=original_tokens,
                source_priority=source_priority,
                allow_english_unknown=allow_english_unknown,
            )
            right_zh = _translate_component_phrase(
                right,
                components=components,
                original_tokens=original_tokens,
                source_priority=source_priority,
                allow_english_unknown=allow_english_unknown,
            )
            if left_zh and right_zh:
                if _redundant_adjacent_translation(left_zh, right_zh):
                    return None
                return f"{right_zh}的{left_zh}"
    out: list[str] = []
    index = 0
    while index < len(tokens):
        matched = ""
        matched_len = 0
        for size in range(min(4, len(tokens) - index), 0, -1):
            chunk = " ".join(tokens[index:index + size])
            if chunk in components:
                matched = components[chunk]
                matched_len = size
                break
            if chunk in EXACT_ALIASES:
                matched = EXACT_ALIASES[chunk]
                matched_len = size
                break
            if size == 1 and source_priority:
                fallback = _priority_token_fallback(
                    chunk,
                    allow_english_unknown=allow_english_unknown,
                    original_token=original_tokens.get(chunk),
                )
                if fallback:
                    matched = fallback
                    matched_len = size
                    break
        if not matched:
            return None
        if out and _redundant_adjacent_translation(out[-1], matched):
            return None
        out.append(matched)
        index += matched_len
    return _join_translated_component_parts(out)


def _propose_alias(
    term: str,
    *,
    domains: Iterable[str] = (),
    biomedical: bool = False,
    allow_compositional: bool = True,
    allow_single_component: bool = False,
    allow_mixed_class_suffix: bool = False,
    source_priority: bool = False,
    allow_english_unknown: bool = False,
) -> tuple[str, str, str] | None:
    key = _key(term)
    key = _uninvert_mesh_label(key)
    if not key or key in GENERIC_EN:
        return None
    components = _components_for_domains(source_priority=source_priority, domains=domains)
    original_tokens = _original_token_forms(term)
    if key in EXACT_ALIASES:
        return EXACT_ALIASES[key], "exact_glossary", "high"
    chromosome_alias = _chromosome_human_pair_alias(key)
    if chromosome_alias:
        return chromosome_alias, "compositional_glossary", "medium"
    influenza_alias = _influenza_virus_alias(key)
    if influenza_alias:
        return influenza_alias, "compositional_glossary", "medium"
    proto_oncogene_alias = _proto_oncogene_protein_alias(key)
    if proto_oncogene_alias:
        return proto_oncogene_alias, "compositional_glossary", "medium"
    cytochrome_alias = _cytochrome_p450_alias(key)
    if cytochrome_alias:
        return cytochrome_alias, "compositional_glossary", "medium"
    as_topic_alias = _as_topic_alias(key, components=components, original_tokens=original_tokens)
    if as_topic_alias:
        return as_topic_alias, "compositional_glossary", "medium"
    gtp_binding_alias = _biomolecular_gtp_binding_alias(key, components=components, original_tokens=original_tokens)
    if gtp_binding_alias:
        return gtp_binding_alias, "compositional_glossary", "medium"
    numbered_alias = _biomedical_numbered_entity_alias(key, components=components, original_tokens=original_tokens)
    if numbered_alias:
        return numbered_alias, "compositional_glossary", "medium"
    if allow_single_component and key in SINGLE_COMPONENT_ALIAS_KEYS and key in components and len(key.split()) == 1:
        return components[key], "single_component_glossary", "medium"
    if not allow_compositional:
        return None
    if biomedical and any(token in BIOMEDICAL_COMPOSITION_BLOCKLIST for token in key.split()):
        return None
    whole_phrase = _translate_component_phrase(
        key,
        components=components,
        original_tokens=original_tokens,
        source_priority=source_priority,
        allow_english_unknown=allow_english_unknown,
    )
    if whole_phrase and len(key.split()) >= 2:
        return whole_phrase, "compositional_glossary", "medium"
    for suffix, zh_suffix in NORMALIZED_SUFFIX_PATTERNS:
        if key == suffix:
            continue
        prefix = ""
        if key.endswith(f" {suffix}"):
            prefix = key[: -(len(suffix) + 1)]
        if not prefix:
            continue
        prefix_zh = _translate_component_phrase(
            prefix,
            components=components,
            original_tokens=original_tokens,
            source_priority=source_priority,
            allow_english_unknown=allow_english_unknown,
        )
        if prefix_zh:
            if _redundant_adjacent_translation(prefix_zh, zh_suffix):
                return None
            return f"{prefix_zh}{zh_suffix}", "compositional_glossary", "medium"
    if allow_mixed_class_suffix:
        mixed_alias = _mixed_class_suffix_alias(key, components=components, original_tokens=original_tokens)
        if mixed_alias:
            return mixed_alias, "mixed_class_suffix", "medium"
        if biomedical:
            mixed_alias = _mixed_class_suffix_alias(
                key,
                components=components,
                original_tokens=original_tokens,
                max_prefix_tokens=8,
                allow_and_token=True,
            )
            if mixed_alias:
                return mixed_alias, "mixed_class_suffix", "medium"
    return None


def _valid_zh_alias(alias: str) -> bool:
    text = _clean_text(alias)
    if text in GENERIC_ZH:
        return False
    if not any("\u4e00" <= char <= "\u9fff" for char in text):
        return False
    return 2 <= len(text) <= 40


def _candidate(alias: str, term: str, method: str, confidence: str, *, source_priority: bool) -> dict[str, str]:
    scope = "source-prioritized" if source_priority else "conservative"
    if method == "exact_glossary":
        reason = f"{scope} exact bilingual glossary"
    elif method == "single_component_glossary":
        reason = f"{scope} single-term technical glossary candidate"
    elif method == "mixed_class_suffix":
        reason = f"{scope} mixed English-Chinese class suffix candidate"
    elif method == "source_label_topic_fallback":
        reason = f"{scope} source-label topic fallback; English label retained for review"
    elif method == "review_gated_mixed_fallback":
        reason = f"{scope} low-confidence mixed English-Chinese fallback for review"
    else:
        reason = f"{scope} compositional technical glossary candidate"
    return {
        "alias": alias,
        "confidence": confidence,
        "evidence_en": term,
        "reason": reason,
        "source": f"agent_{method}",
        "status": "candidate",
    }


def _source_label_topic_fallback(row: dict[str, Any]) -> dict[str, str] | None:
    # Disabled by policy: this shape keeps the English label and only appends
    # "主题", so it creates review noise rather than a real Chinese alias.
    if not _priority_source(row):
        return None
    return None
    term = _clean_text(row.get("canonical_en") or "")
    if not term or _key(term) in GENERIC_EN:
        return None
    key_tokens = _key(term).split()
    if any(left == right for left, right in zip(key_tokens, key_tokens[1:])):
        return None
    components = _components_for_domains(source_priority=True, domains=row.get("domains") or [])
    for left, right in zip(key_tokens, key_tokens[1:]):
        if left in components and right in components and _redundant_adjacent_translation(components[left], components[right]):
            return None
    if _short_single_source_label(term):
        return None
    alias = f"{_source_label_display(term)}主题"
    if not _valid_zh_alias(alias):
        return None
    return _candidate(
        alias,
        term,
        "source_label_topic_fallback",
        "low",
        source_priority=True,
    )


def _review_gated_mixed_fallback(row: dict[str, Any]) -> dict[str, str] | None:
    if _priority_source(row):
        return None
    for term, is_canonical in _english_terms(row):
        if not is_canonical:
            continue
        term = _clean_text(term)
        key_tokens = _key(term).split()
        if len(key_tokens) < 2:
            continue
        if " ".join(key_tokens) in GENERIC_EN:
            continue
        if "agent" in key_tokens:
            continue
        if _is_biomedical_row(row) and set(key_tokens) & {"algorithm", "framework"}:
            continue
        if any(left == right for left, right in zip(key_tokens, key_tokens[1:])):
            continue
        if _short_single_source_label(term):
            continue
        proposed = _propose_alias(
            term,
            domains=row.get("domains") or [],
            biomedical=_is_biomedical_row(row),
            allow_compositional=True,
            allow_single_component=False,
            allow_mixed_class_suffix=True,
            source_priority=True,
            allow_english_unknown=True,
        )
        if not proposed:
            continue
        alias, _method, _confidence = proposed
        if not _valid_zh_alias(alias):
            continue
        if _non_acronym_ascii_segment_count(alias) > 0:
            continue
        return _candidate(
            alias,
            term,
            "review_gated_mixed_fallback",
            "low",
            source_priority=False,
        )
    return None


def _fill_row(row: dict[str, Any], *, replace_generated: bool = False) -> tuple[bool, bool]:
    replaced = False
    if replace_generated and not row.get("zh_alias_candidates") and row.get("candidate_generation_status") in GENERATED_STATUSES:
        row["candidate_generation_status"] = "pending_host_agent"
        replaced = True
    if row.get("zh_alias_candidates"):
        if not replace_generated or not _generated_candidates(row):
            return False, False
        row["zh_alias_candidates"] = []
        row["candidate_generation_status"] = "pending_host_agent"
        replaced = True
    source_priority = _priority_source(row)
    biomedical = _is_biomedical_row(row)
    technical_priority = _is_technical_priority_row(row)
    allow_english_unknown = source_priority
    max_candidates = int(row.get("max_zh_alias_candidates") or DEFAULT_MAX_CANDIDATES)
    proposals: list[dict[str, str]] = []
    seen_aliases: set[str] = set()
    for term, is_canonical in _english_terms(row):
        allow_compositional = source_priority or is_canonical
        proposed = _propose_alias(
            term,
            domains=row.get("domains") or [],
            biomedical=biomedical,
            allow_compositional=allow_compositional,
            allow_single_component=source_priority,
            allow_mixed_class_suffix=source_priority or is_canonical,
            source_priority=source_priority,
            allow_english_unknown=allow_english_unknown,
        )
        if not proposed:
            continue
        alias, method, confidence = proposed
        if (
            source_priority
            and not technical_priority
            and method == "compositional_glossary"
            and _non_acronym_ascii_segment_count(alias) > 1
        ):
            continue
        if method != "exact_glossary" and _non_acronym_ascii_segment_count(alias) > 0:
            continue
        if not _valid_zh_alias(alias) or alias in seen_aliases:
            continue
        seen_aliases.add(alias)
        proposals.append(_candidate(alias, term, method, confidence, source_priority=source_priority))
        if not source_priority and method == "exact_glossary" and confidence == "high":
            break
        if len(proposals) >= max(0, min(DEFAULT_MAX_CANDIDATES, max_candidates)):
            break
    if not proposals:
        fallback = _source_label_topic_fallback(row)
        if fallback:
            row["zh_alias_candidates"] = [fallback]
            row["candidate_generation_status"] = "source_priority_generated"
            return True, replaced
        fallback = _review_gated_mixed_fallback(row)
        if fallback:
            row["zh_alias_candidates"] = [fallback]
            row["candidate_generation_status"] = "conservative_generated"
            return True, replaced
        return False, replaced
    row["zh_alias_candidates"] = proposals
    row["candidate_generation_status"] = "source_priority_generated" if source_priority else "conservative_generated"
    return True, replaced


def fill_zh_alias_candidates(candidate_dir: Path, *, replace_generated: bool = False) -> dict[str, Any]:
    candidate_dir = Path(candidate_dir)
    files = _candidate_files(candidate_dir)
    records_seen = 0
    records_filled = 0
    records_replaced = 0
    files_changed = 0
    for path in files:
        rows = _read_jsonl(path)
        changed = False
        for row in rows:
            records_seen += 1
            filled, replaced = _fill_row(row, replace_generated=replace_generated)
            if replaced:
                records_replaced += 1
                changed = True
            if filled:
                records_filled += 1
                changed = True
        if changed:
            _write_jsonl(path, rows)
            files_changed += 1
    summary = {
        "schema_version": "theme_zh_alias_fill.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "candidate_dir": str(candidate_dir.resolve()),
        "files_considered": len(files),
        "files_changed": files_changed,
        "records_seen": records_seen,
        "records_filled": records_filled,
        "records_replaced": records_replaced,
        "strategy": "review_gated_conservative_glossary",
        "priority_sources": sorted(PRIORITY_SOURCES),
    }
    manifest_path = candidate_dir / "zh_alias_fill_manifest.json"
    summary["manifest"] = str(manifest_path)
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", type=Path, default=Path("lexicons/candidates"))
    parser.add_argument(
        "--replace-generated",
        action="store_true",
        help="Recompute rows whose existing zh aliases were generated by this offline agent script.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = fill_zh_alias_candidates(candidate_dir=args.candidate_dir, replace_generated=args.replace_generated)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
