from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


DATASETS = [
    # Image Classification
    {
        'id': 'cifar-10',
        'name': 'CIFAR-10',
        'description': '加拿大高等研究院（CIFAR）发布的图像分类数据集，包含10个类别共60,000张32x32彩色图像，每个类别6,000张图片。广泛应用于机器学习研究和教育。',
        'category': 'image_classification',
        'domain': '计算机视觉',
        'format': 'PNG',
        'size': '~170 MB',
        'samples': '60,000 张图片',
        'source': 'Official',
        'url': 'https://www.cs.toronto.edu/~kriz/cifar.html',
        'license': 'Unknown'
    },
    {
        'id': 'imagenet',
        'name': 'ImageNet',
        'description': '计算机视觉领域最著名的图像数据集之一，包含超过1400万张手工标注的高分辨率图像，涵盖2万多个类别。是深度学习革命的重要推动者。',
        'category': 'image_classification',
        'domain': '计算机视觉',
        'format': 'JPEG',
        'size': '~150 GB',
        'samples': '14,197,122 张图片',
        'source': 'Official',
        'url': 'https://www.image-net.org/',
        'license': 'Research Only'
    },
    {
        'id': 'mnist',
        'name': 'MNIST',
        'description': '手写数字识别的经典入门数据集，包含0-9的手写数字图像。数据集规模适中，入门友好，是机器学习入门的必选数据集。',
        'category': 'image_classification',
        'domain': '计算机视觉',
        'format': 'PNG',
        'size': '~11 MB',
        'samples': '70,000 张图片',
        'source': 'Kaggle',
        'url': 'https://www.kaggle.com/datasets/hojjatk/mnist-dataset',
        'license': 'Unknown'
    },
    {
        'id': 'fashion-mnist',
        'name': 'Fashion-MNIST',
        'description': 'Zalando发布的时尚物品图像数据集，是MNIST的替代品。包含10个类别共70,000张28x28灰度图像，比MNIST更具挑战性。',
        'category': 'image_classification',
        'domain': '时尚/电商',
        'format': 'PNG',
        'size': '~30 MB',
        'samples': '70,000 张图片',
        'source': 'Official',
        'url': 'https://github.com/zalandoresearch/fashion-mnist',
        'license': 'MIT'
    },
    {
        'id': 'food-101',
        'name': 'Food-101',
        'description': '食品图像分类数据集，包含101个食品类别共101,000张图像。每个类别有250张测试图像和750张训练图像。',
        'category': 'image_classification',
        'domain': '食品识别',
        'format': 'JPEG',
        'size': '~5 GB',
        'samples': '101,000 张图片',
        'source': 'Kaggle',
        'url': 'https://www.kaggle.com/datasets/dansbecker/food-101',
        'license': 'Unknown'
    },
    {
        'id': 'oxford-pets',
        'name': 'Oxford Pets',
        'description': '牛津大学发布的宠物图像数据集，包含37种宠物共7,400张图像，每个类别约200张图片。适用于图像分类和细粒度识别研究。',
        'category': 'image_classification',
        'domain': '宠物识别',
        'format': 'JPEG',
        'size': '~800 MB',
        'samples': '7,390 张图片',
        'source': 'Official',
        'url': 'https://www.robots.ox.ac.uk/~vgg/data/pets/',
        'license': 'Creative Commons'
    },

    # Object Detection
    {
        'id': 'coco',
        'name': 'COCO',
        'description': '微软发布的通用物体检测、分割和字幕数据集，是目标检测领域最权威的数据集。包含330K张图像，涵盖80个物体类别，支持目标检测、实例分割等任务。',
        'category': 'object_detection',
        'domain': '计算机视觉',
        'format': 'JSON+COCO',
        'size': '~40 GB',
        'samples': '330K 张图片',
        'source': 'Official',
        'url': 'https://cocodataset.org/',
        'license': 'Creative Commons'
    },
    {
        'id': 'pascal-voc',
        'name': 'Pascal VOC',
        'description': '视觉物体分类挑战赛数据集，包含20个物体类别的图像，带有边界框和分割标注。广泛用于目标检测和语义分割研究。',
        'category': 'object_detection',
        'domain': '计算机视觉',
        'format': 'VOC',
        'size': '~2 GB',
        'samples': '11,530 张图片',
        'source': 'Official',
        'url': 'https://pjreddie.com/projects/pascal-voc-dataset-mirror/',
        'license': 'Creative Commons'
    },
    {
        'id': 'open-images',
        'name': 'Open Images',
        'description': 'Google发布的大规模图像数据集，包含900万张图像，涵盖19,959个类别的标注。是目前最大的公开图像数据集之一。',
        'category': 'object_detection',
        'domain': '计算机视觉',
        'format': 'CSV+Image',
        'size': '~500 GB',
        'samples': '9,000,000 张图片',
        'source': 'Official',
        'url': 'https://storage.googleapis.com/openimages/web/index.html',
        'license': 'Creative Commons'
    },

    # NLP
    {
        'id': 'imdb-reviews',
        'name': 'IMDB Reviews',
        'description': '电影评论情感分析数据集，包含50,000条电影评论，其中25,000条正面评论和25,000条负面评论。文本分类的经典入门数据集。',
        'category': 'nlp',
        'domain': '情感分析',
        'format': 'TXT',
        'size': '~80 MB',
        'samples': '50,000 条评论',
        'source': 'Kaggle',
        'url': 'https://www.kaggle.com/datasets/lakshmi25npathi/imdb-dataset-of-50k-movie-reviews',
        'license': 'Unknown'
    },
    {
        'id': 'squad',
        'name': 'SQuAD',
        'description': '斯坦福问答数据集，包含10万多个问答对，基于维基百科文章。问答对需要从给定段落中提取答案，是阅读理解的权威数据集。',
        'category': 'nlp',
        'domain': '问答系统',
        'format': 'JSON',
        'size': '~40 MB',
        'samples': '100,000+ 问答对',
        'source': 'Official',
        'url': 'https://rajpurkar.github.io/SQuAD-explorer/',
        'license': 'Creative Commons'
    },
    {
        'id': 'glue',
        'name': 'GLUE Benchmark',
        'description': '通用语言理解评估基准，包含9个自然语言理解任务，如情感分析、文本蕴含、相似度计算等。是评估语言模型的重要标准。',
        'category': 'nlp',
        'domain': '自然语言理解',
        'format': 'TSV',
        'size': '~350 MB',
        'samples': '多种任务',
        'source': 'HuggingFace',
        'url': 'https://huggingface.co/datasets/nyu-mll/glue',
        'license': 'Various'
    },
    {
        'id': 'conll-2003',
        'name': 'CoNLL-2003',
        'description': '命名实体识别经典数据集，源自路透社新闻语料库。包含人名、地名、组织名和杂项实体的标注，是NER任务的基准数据集。',
        'category': 'nlp',
        'domain': '命名实体识别',
        'format': 'CoNLL',
        'size': '~15 MB',
        'samples': '22,000+ 句子',
        'source': 'Kaggle',
        'url': 'https://www.kaggle.com/datasets/rajarshc/roona',
        'license': 'Research Only'
    },

    # Speech
    {
        'id': 'librispeech',
        'name': 'LibriSpeech',
        'description': '从LibriVox有声书项目中提取的语音数据集，包含约1000小时的英语朗读语音。数据已按说话者分好，适合语音识别研究。',
        'category': 'speech',
        'domain': '语音识别',
        'format': 'FLAC',
        'size': '~80 GB',
        'samples': '约 1000 小时',
        'source': 'Official',
        'url': 'https://www.openslr.org/12/',
        'license': 'LibriVox'
    },
    {
        'id': 'common-voice',
        'name': 'Common Voice',
        'description': 'Mozilla发布的开源语音数据集，通过众包方式收集。包含超过100种语言的语音数据，是目前最大的多语言开源语音数据集。',
        'category': 'speech',
        'domain': '语音识别',
        'format': 'MP3',
        'size': '~100+ GB',
        'samples': '100,000+ 小时',
        'source': 'Official',
        'url': 'https://commonvoice.mozilla.org/datasets',
        'license': 'CC0'
    },

    # Tabular
    {
        'id': 'titanic',
        'name': 'Titanic',
        'description': '泰坦尼克号乘客生存预测经典数据集，包含乘客个人信息如姓名、年龄、性别、船票等。是机器学习入门的必选数据集。',
        'category': 'tabular',
        'domain': '预测分析',
        'format': 'CSV',
        'size': '~10 KB',
        'samples': '891 条记录',
        'source': 'Kaggle',
        'url': 'https://www.kaggle.com/datasets/hesh97/titanicdataset-traincsv',
        'license': 'Unknown'
    },
    {
        'id': 'house-prices',
        'name': 'Kaggle House Prices',
        'description': '房价预测竞赛数据集，包含爱荷华州艾姆斯市的住宅特征和售价。适用于回归问题研究，包含80多个特征变量。',
        'category': 'tabular',
        'domain': '预测分析',
        'format': 'CSV',
        'size': '~500 KB',
        'samples': '1,460 条记录',
        'source': 'Kaggle',
        'url': 'https://www.kaggle.com/competitions/house-prices-advanced-regression-techniques',
        'license': 'CC0'
    },

    # Recommendation
    {
        'id': 'movielens',
        'name': 'MovieLens',
        'description': 'GroupLens研究实验室发布的电影评分数据集，是推荐系统研究的经典数据集。包含用户对电影的评分和标签信息。',
        'category': 'recommendation',
        'domain': '推荐系统',
        'format': 'CSV',
        'size': '~20 MB',
        'samples': '27,000,000 条评分',
        'source': 'Official',
        'url': 'https://grouplens.org/datasets/movielens/',
        'license': 'CC0'
    }
]


class DatasetListView(APIView):
    """获取数据集列表，支持分类和搜索过滤"""
    permission_classes = [AllowAny]

    def get(self, request):
        category = request.query_params.get('category', 'all')
        search = request.query_params.get('search', '')

        datasets = DATASETS

        # 按分类过滤
        if category and category != 'all':
            datasets = [d for d in datasets if d['category'] == category]

        # 按搜索关键词过滤
        if search:
            search_lower = search.lower()
            datasets = [
                d for d in datasets
                if search_lower in d['name'].lower()
                or search_lower in d['description'].lower()
                or search_lower in d['domain'].lower()
                or search_lower in d['category'].lower()
            ]

        return Response(datasets)


class CategoryListView(APIView):
    """获取所有分类"""
    permission_classes = [AllowAny]

    def get(self, request):
        categories = [
            {'id': 'all', 'name': '全部'},
            {'id': 'image_classification', 'name': '图像分类'},
            {'id': 'object_detection', 'name': '目标检测'},
            {'id': 'nlp', 'name': '自然语言处理'},
            {'id': 'speech', 'name': '语音识别'},
            {'id': 'text_classification', 'name': '文本分类'},
            {'id': 'tabular', 'name': '表格数据'},
            {'id': 'recommendation', 'name': '推荐系统'},
        ]
        return Response(categories)
