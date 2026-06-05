"""
Real data augmentation implementations for images, text, and tabular data.
"""

import os
import io
import uuid
import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# Image Augmentation
# =============================================================================

class ImageAugmentor:
    """
    Real image augmentation using albumentations library with PIL fallback.
    Supports geometric, color, noise, and mixup transformations.
    """

    def __init__(self, strategy: str = 'all', ratio: float = 2.0, transformations: List[str] = None):
        self.strategy = strategy
        self.ratio = ratio
        self.transformations = transformations or []
        self.transform = None
        self.albumentations_available = False
        self._setup_transforms()

    def _setup_transforms(self):
        """Build augmentation pipeline based on strategy and transformations."""
        try:
            import albumentations as A
            self.albumentations_available = True
            self._setup_albumentations()
        except ImportError:
            logger.warning("albumentations not available, using PIL fallback")
            self._setup_pil_fallback()

    def _setup_albumentations(self):
        """Setup albumentations pipeline."""
        import albumentations as A

        transforms_list = []

        if self.strategy in ['geometric', 'all'] or self._has_transform('rotate'):
            transforms_list.extend([
                A.Rotate(limit=15, p=0.5),
                A.Rotate(limit=(-15, -5), p=0.3),
            ])

        if self.strategy in ['geometric', 'all'] or self._has_transform('flip_horizontal'):
            transforms_list.append(A.HorizontalFlip(p=0.5))

        if self.strategy in ['geometric', 'all'] or self._has_transform('flip_vertical'):
            transforms_list.append(A.VerticalFlip(p=0.5))

        if self.strategy in ['geometric', 'all'] or self._has_transform('scale'):
            transforms_list.append(A.Affine(scale=(0.9, 1.1), p=0.5))

        if self.strategy in ['geometric', 'all'] or self._has_transform('crop'):
            transforms_list.append(A.RandomCrop(height=224, width=224, p=0.3))

        if self.strategy in ['geometric', 'all'] or self._has_transform('translate'):
            transforms_list.append(A.Affine(translate_percent=(0.05, 0.05), p=0.3))

        if self.strategy in ['color', 'all'] or self._has_transform('brightness'):
            transforms_list.append(A.RandomBrightnessContrast(brightness_limit=0.2, p=0.5))

        if self.strategy in ['color', 'all'] or self._has_transform('contrast'):
            transforms_list.append(A.RandomBrightnessContrast(contrast_limit=0.2, p=0.5))

        if self.strategy in ['color', 'all'] or self._has_transform('saturation'):
            transforms_list.append(A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=20, p=0.5))

        if self.strategy in ['color', 'all'] or self._has_transform('grayscale'):
            transforms_list.append(A.ToGray(p=0.2))

        if self.strategy in ['noise', 'all'] or self._has_transform('gaussian_noise'):
            transforms_list.append(A.GaussNoise(var_limit=(10.0, 50.0), p=0.3))

        if self.strategy in ['noise', 'all'] or self._has_transform('random_erasing'):
            transforms_list.append(A.RandomErasing(p=0.3, scale=(0.02, 0.15)))

        if not transforms_list:
            transforms_list = [
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(p=0.3),
                A.RandomBrightnessContrast(p=0.5),
                A.GaussNoise(var_limit=(10.0, 50.0), p=0.3),
            ]

        self.transform = A.Compose(transforms_list)

    def _setup_pil_fallback(self):
        """Setup PIL-based fallback transforms."""
        self.pil_transforms = []
        
        if self.strategy in ['geometric', 'all'] or self._has_transform('rotate'):
            self.pil_transforms.append('rotate')
        if self.strategy in ['geometric', 'all'] or self._has_transform('flip_horizontal'):
            self.pil_transforms.append('flip_h')
        if self.strategy in ['geometric', 'all'] or self._has_transform('flip_vertical'):
            self.pil_transforms.append('flip_v')
        if self.strategy in ['color', 'all'] or self._has_transform('brightness'):
            self.pil_transforms.append('brightness')
        if self.strategy in ['color', 'all'] or self._has_transform('contrast'):
            self.pil_transforms.append('contrast')
        if self.strategy in ['noise', 'all'] or self._has_transform('gaussian_noise'):
            self.pil_transforms.append('noise')
        
        if not self.pil_transforms:
            self.pil_transforms = ['flip_h', 'flip_v', 'brightness']

    def _has_transform(self, name: str) -> bool:
        """Check if a specific transform is requested."""
        return name.lower() in [t.lower() for t in self.transformations]

    def augment_image(self, image_path: str, output_dir: str) -> List[str]:
        """
        Augment a single image and return paths of augmented images.
        
        Args:
            image_path: Path to the input image
            output_dir: Directory to save augmented images
            
        Returns:
            List of paths to augmented images
        """
        try:
            from PIL import Image
        except ImportError:
            logger.error("PIL not available")
            return []

        output_paths = []
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            if self.albumentations_available:
                output_paths = self._augment_with_albumentations(image_path, output_dir)
            else:
                output_paths = self._augment_with_pil(image_path, output_dir)
        except Exception as e:
            logger.error(f"Error augmenting image {image_path}: {e}")

        return output_paths

    def _augment_with_albumentations(self, image_path: str, output_dir: Path) -> List[str]:
        """Augment using albumentations."""
        import cv2
        from PIL import Image

        image = cv2.imread(str(image_path))
        if image is None:
            try:
                pil_img = Image.open(image_path)
                image = np.array(pil_img)
                if len(image.shape) == 2:
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
                elif image.shape[2] == 4:
                    image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
                else:
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            except Exception as e:
                logger.error(f"Failed to read image: {e}")
                return []

        output_paths = []
        num_augmented = int(self.ratio)

        for i in range(num_augmented):
            try:
                augmented = self.transform(image=image)
                aug_image = augmented['image']
                
                aug_image_rgb = cv2.cvtColor(aug_image, cv2.COLOR_BGR2RGB)
                output_name = f"{Path(image_path).stem}_aug_{i}_{uuid.uuid4().hex[:8]}.jpg"
                output_path = output_dir / output_name
                
                cv2.imwrite(str(output_path), aug_image_rgb)
                output_paths.append(str(output_path))
            except Exception as e:
                logger.warning(f"Augmentation {i} failed: {e}")
                continue

        return output_paths

    def _augment_with_pil(self, image_path: str, output_dir: Path) -> List[str]:
        """Augment using PIL fallback."""
        from PIL import Image, ImageEnhance, ImageOps

        output_paths = []
        num_augmented = int(self.ratio)

        try:
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
        except Exception as e:
            logger.error(f"Failed to open image: {e}")
            return []

        for i in range(num_augmented):
            try:
                aug_image = image.copy()
                transform_name = random.choice(self.pil_transforms)

                if transform_name == 'rotate':
                    angle = random.uniform(-15, 15)
                    aug_image = aug_image.rotate(angle)
                elif transform_name == 'flip_h':
                    aug_image = ImageOps.mirror(aug_image)
                elif transform_name == 'flip_v':
                    aug_image = ImageOps.flip(aug_image)
                elif transform_name == 'brightness':
                    factor = random.uniform(0.8, 1.2)
                    enhancer = ImageEnhance.Brightness(aug_image)
                    aug_image = enhancer.enhance(factor)
                elif transform_name == 'contrast':
                    factor = random.uniform(0.8, 1.2)
                    enhancer = ImageEnhance.Contrast(aug_image)
                    aug_image = enhancer.enhance(factor)
                elif transform_name == 'noise':
                    img_array = np.array(aug_image)
                    noise = np.random.normal(0, 10, img_array.shape)
                    noisy_img = np.clip(img_array + noise, 0, 255).astype(np.uint8)
                    aug_image = Image.fromarray(noisy_img)

                output_name = f"{Path(image_path).stem}_aug_{i}_{uuid.uuid4().hex[:8]}.jpg"
                output_path = output_dir / output_name
                aug_image.save(str(output_path), quality=95)
                output_paths.append(str(output_path))
            except Exception as e:
                logger.warning(f"PIL augmentation {i} failed: {e}")
                continue

        return output_paths

    def augment_dataset(self, input_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Augment entire image dataset directory.
        
        Args:
            input_path: Path to directory containing images
            output_dir: Directory to save augmented images
            
        Returns:
            Statistics about the augmentation
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
        image_files = [
            f for f in input_path.rglob('*')
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        total_original = len(image_files)
        total_augmented = 0
        all_output_files = []

        for img_file in image_files:
            aug_paths = self.augment_image(str(img_file), str(output_dir))
            total_augmented += len(aug_paths)
            all_output_files.extend(aug_paths)

        return {
            'original_count': total_original,
            'augmented_count': total_augmented,
            'total_count': total_original + total_augmented,
            'output_dir': str(output_dir),
            'output_files': all_output_files,
            'strategy': self.strategy,
            'ratio': self.ratio,
        }


# =============================================================================
# Text Augmentation
# =============================================================================

class TextAugmentor:
    """
    Text augmentation using synonym replacement, random insertion, 
    random swap, and back-translation (stub).
    """

    SYNONYM_DICT = {
        'good': ['great', 'excellent', 'wonderful', 'positive'],
        'bad': ['poor', 'terrible', 'negative', 'awful'],
        'big': ['large', 'huge', 'enormous', 'massive'],
        'small': ['tiny', 'little', 'miniature', 'compact'],
        'fast': ['quick', 'rapid', 'swift', 'speedy'],
        'slow': ['gradual', 'leisurely', 'unhurried'],
        'happy': ['joyful', 'pleased', 'delighted', 'content'],
        'sad': ['unhappy', 'sorrowful', 'melancholy', 'down'],
        'important': ['significant', 'crucial', 'essential', 'vital'],
        'easy': ['simple', 'straightforward', 'effortless'],
        'difficult': ['hard', 'challenging', 'tough', 'demanding'],
        'beautiful': ['gorgeous', 'lovely', 'stunning', 'attractive'],
        'ugly': ['unsightly', 'unpleasant', 'hideous'],
        'old': ['ancient', 'aged', 'elderly', 'mature'],
        'new': ['fresh', 'recent', 'modern', 'novel'],
        'strong': ['powerful', 'mighty', 'robust', 'tough'],
        'weak': ['feeble', 'frail', 'fragile', 'delicate'],
        'rich': ['wealthy', 'affluent', 'prosperous'],
        'poor': ['impoverished', 'needy', 'destitute'],
        'high': ['tall', 'elevated', 'lofty', 'towering'],
        'low': ['short', 'lowly', 'shallow'],
        'long': ['extended', 'lengthy', 'prolonged'],
        'short': ['brief', 'concise', 'curtailed'],
        'hot': ['warm', 'scorching', 'searing', 'burning'],
        'cold': ['chilly', 'cool', 'freezing', 'icy'],
        'bright': ['brilliant', 'vivid', 'radiant', 'luminous'],
        'dark': ['dim', 'shadowy', 'gloomy', 'murky'],
        'clean': ['spotless', 'tidy', 'neat', 'pristine'],
        'dirty': ['soiled', 'grimy', 'filthy', 'unclean'],
        'smart': ['intelligent', 'clever', 'bright', 'wise'],
        'stupid': ['foolish', 'silly', 'dumb', 'unintelligent'],
        'interesting': ['fascinating', 'intriguing', 'engaging', 'compelling'],
        'boring': ['dull', 'tedious', 'monotonous', 'uninteresting'],
        'like': ['enjoy', 'love', 'appreciate', 'prefer'],
        'dislike': ['hate', 'detest', 'disapprove', 'loathe'],
        'think': ['believe', 'consider', 'suppose', 'reckon'],
        'see': ['observe', 'witness', 'notice', 'perceive'],
        'know': ['understand', 'comprehend', 'recognize', 'realize'],
        'want': ['desire', 'wish', 'need', 'crave'],
        'make': ['create', 'produce', 'build', 'construct'],
        'take': ['grab', 'seize', 'capture', 'obtain'],
        'come': ['arrive', 'approach', 'reach', 'enter'],
        'go': ['move', 'proceed', 'travel', 'journey'],
        'use': ['utilize', 'employ', 'apply', 'adopt'],
        'find': ['discover', 'locate', 'detect', 'identify'],
        'give': ['provide', 'offer', 'present', 'deliver'],
        'tell': ['inform', 'notify', 'advise', 'notify'],
        'ask': ['inquire', 'question', 'query', 'probe'],
        'work': ['labor', 'toil', 'function', 'operate'],
        'play': ['engage', 'participate', 'perform', 'act'],
        'run': ['sprint', 'dash', 'race', 'hurry'],
        'move': ['shift', 'transfer', 'relocate', 'adjust'],
        'live': ['reside', 'dwell', 'inhabit', 'stay'],
        'believe': ['trust', 'rely', 'count', 'depend'],
        'hold': ['grasp', 'grip', 'clutch', 'embrace'],
        'bring': ['carry', 'fetch', 'convey', 'transport'],
        'happen': ['occur', 'transpire', 'take place', 'arise'],
        'write': ['compose', 'author', 'draft', 'pen'],
        'provide': ['supply', 'furnish', 'give', 'offer'],
        'sit': ['rest', 'settle', 'position', 'perch'],
        'stand': ['rise', 'arise', 'stand up', 'erect'],
        'lose': ['miscoordinate', 'misplace', 'forfeit', 'drop'],
        'pay': ['remit', 'compensate', 'reimburse', 'settle'],
        'meet': ['encounter', 'gather', 'assemble', 'converge'],
        'include': ['contain', 'incorporate', 'comprise', 'encompass'],
        'continue': ['proceed', 'persist', 'resume', 'carry on'],
        'set': ['establish', 'fix', 'determine', 'adjust'],
        'learn': ['acquire', 'master', 'absorb', 'grasp'],
        'change': ['alter', 'modify', 'transform', 'adjust'],
        'lead': ['guide', 'direct', 'steer', 'govern'],
        'understand': ['comprehend', 'grasp', 'realize', 'appreciate'],
        'watch': ['observe', 'view', 'monitor', 'scrutinize'],
        'follow': ['track', 'pursue', 'trail', 'shadow'],
        'stop': ['cease', 'halt', 'pause', 'terminate'],
        'create': ['generate', 'produce', 'establish', 'build'],
        'speak': ['talk', 'communicate', 'converse', 'express'],
        'read': ['peruse', 'study', 'examine', 'scan'],
        'spend': ['expend', 'invest', 'allocate', 'consume'],
        'grow': ['expand', 'develop', 'increase', 'flourish'],
        'open': ['unseal', 'unlock', 'expose', 'uncover'],
        'walk': ['stroll', 'march', 'stride', 'amble'],
        'win': ['triumph', 'prevail', 'succeed', 'conquer'],
        'offer': ['provide', 'present', 'propose', 'suggest'],
        'remember': ['recall', 'recollect', 'retain', 'memorize'],
        'love': ['adore', 'cherish', 'appreciate', 'value'],
        'consider': ['contemplate', 'reflect', 'deliberate', 'ponder'],
        'appear': ['emerge', 'surface', 'show up', 'materialize'],
        'buy': ['purchase', 'acquire', 'obtain', 'procure'],
        'wait': ['await', 'stay', 'remain', 'pause'],
        'serve': ['assist', 'help', 'aid', 'support'],
        'die': ['expire', 'perish', 'pass away', 'cease'],
        'send': ['dispatch', 'transmit', 'forward', 'convey'],
        'expect': ['anticipate', 'await', 'predict', 'foresee'],
        'build': ['construct', 'establish', 'create', 'develop'],
        'stay': ['remain', 'reside', 'linger', 'dwell'],
        'fall': ['drop', 'tumble', 'descend', 'plunge'],
        'cut': ['slice', 'chop', 'trim', 'sever'],
        'reach': ['attain', 'achieve', 'arrive', 'extend'],
        'kill': ['terminate', 'eliminate', 'destroy', 'end'],
        'remain': ['persist', 'stay', 'continue', 'endure'],
        'suggest': ['propose', 'recommend', 'advise', 'hint'],
        'raise': ['lift', 'elevate', 'boost', 'increase'],
        'pass': ['proceed', 'elapse', 'transcend', 'surpass'],
        'sell': ['trade', 'market', 'vend', 'merchandise'],
        'require': ['need', 'demand', 'necessitate', 'compel'],
        'report': ['describe', 'relate', 'narrate', 'account'],
        'decide': ['determine', 'resolve', 'conclude', 'choose'],
        'pull': ['tug', 'drag', 'draw', 'extract'],
    }

    def __init__(self, strategy: str = 'all', ratio: float = 2.0, transformations: List[str] = None):
        self.strategy = strategy
        self.ratio = ratio
        self.transformations = transformations or ['synonym_replacement', 'random_swap']

    def augment_text(self, text: str) -> List[str]:
        """
        Augment a single text using multiple strategies.
        
        Args:
            text: Input text
            
        Returns:
            List of augmented texts
        """
        augmented_texts = []
        num_augmented = int(self.ratio)

        strategies = []
        if self.strategy == 'all':
            strategies = ['synonym_replacement', 'random_swap', 'random_insertion']
        else:
            strategies = [self.strategy]

        for i in range(num_augmented):
            aug_text = text
            for strategy in strategies:
                if strategy == 'synonym_replacement':
                    aug_text = self.synonym_replacement(aug_text, n=2)
                elif strategy == 'random_swap':
                    aug_text = self.random_swap(aug_text, n=2)
                elif strategy == 'random_insertion':
                    aug_text = self.random_insertion(aug_text, n=2)
            augmented_texts.append(aug_text)

        return augmented_texts

    def synonym_replacement(self, text: str, n: int = 3) -> str:
        """
        Replace n random words with synonyms.
        
        Args:
            text: Input text
            n: Number of words to replace
            
        Returns:
            Text with replaced words
        """
        words = text.split()
        if len(words) < 2:
            return text

        candidates = []
        for i, word in enumerate(words):
            word_lower = word.lower().strip('.,!?;:')
            if word_lower in self.SYNONYM_DICT:
                candidates.append(i)

        if not candidates:
            return text

        num_to_replace = min(n, len(candidates))
        indices_to_replace = random.sample(candidates, num_to_replace)

        result_words = words.copy()
        for idx in indices_to_replace:
            word_lower = result_words[idx].lower().strip('.,!?;:')
            if word_lower in self.SYNONYM_DICT:
                synonyms = self.SYNONYM_DICT[word_lower]
                replacement = random.choice(synonyms)
                original = result_words[idx]
                if original.isupper():
                    replacement = replacement.upper()
                elif original[0].isupper():
                    replacement = replacement.capitalize()
                result_words[idx] = replacement

        return ' '.join(result_words)

    def random_insertion(self, text: str, n: int = 3) -> str:
        """
        Randomly insert n words into text.
        
        Args:
            text: Input text
            n: Number of words to insert
            
        Returns:
            Text with inserted words
        """
        words = text.split()
        if len(words) < 2:
            return text

        all_synonyms = []
        for synonyms in self.SYNONYM_DICT.values():
            all_synonyms.extend(synonyms)

        if not all_synonyms:
            return text

        for _ in range(n):
            if not words:
                break
            pos = random.randint(0, len(words))
            word = random.choice(all_synonyms)
            words.insert(pos, word)

        return ' '.join(words)

    def random_swap(self, text: str, n: int = 3) -> str:
        """
        Randomly swap n pairs of words.
        
        Args:
            text: Input text
            n: Number of pairs to swap
            
        Returns:
            Text with swapped words
        """
        words = text.split()
        if len(words) < 2:
            return text

        result_words = words.copy()

        for _ in range(n):
            if len(result_words) < 2:
                break
            i, j = random.sample(range(len(result_words)), 2)
            result_words[i], result_words[j] = result_words[j], result_words[i]

        return ' '.join(result_words)

    def back_translation(self, text: str) -> str:
        """
        Back-translate text (stub implementation).
        In production, this would use a translation API.
        
        Args:
            text: Input text
            
        Returns:
            Back-translated text (original for now)
        """
        logger.warning("Back-translation API not implemented, returning original text")
        return text

    def augment_dataset(self, input_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Augment text dataset.
        
        Args:
            input_path: Path to input file (.txt, .json, .csv)
            output_dir: Directory to save augmented texts
            
        Returns:
            Statistics about the augmentation
        """
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        all_texts = []
        
        if input_path.suffix == '.txt':
            with open(input_path, 'r', encoding='utf-8') as f:
                all_texts = [line.strip() for line in f if line.strip()]
        elif input_path.suffix == '.json':
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_texts = [item.get('text', item.get('content', '')) for item in data]
                elif isinstance(data, dict):
                    all_texts = [data.get('text', data.get('content', ''))]
        elif input_path.suffix == '.csv':
            import pandas as pd
            df = pd.read_csv(input_path)
            text_col = 'text' if 'text' in df.columns else 'content' if 'content' in df.columns else df.columns[0]
            all_texts = df[text_col].dropna().tolist()

        total_original = len(all_texts)
        all_augmented = []

        for text in all_texts:
            aug_texts = self.augment_text(text)
            all_augmented.extend(aug_texts)

        output_file = output_dir / f"augmented_{input_path.stem}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_augmented))

        return {
            'original_count': total_original,
            'augmented_count': len(all_augmented),
            'total_count': total_original + len(all_augmented),
            'output_file': str(output_file),
            'strategy': self.strategy,
            'ratio': self.ratio,
        }


# =============================================================================
# Tabular Augmentation
# =============================================================================

class TabularAugmentor:
    """
    Tabular data augmentation using SMOTE, noise injection, 
    or row duplication with modifications.
    """

    def __init__(self, strategy: str = 'all', ratio: float = 2.0, transformations: List[str] = None):
        self.strategy = strategy
        self.ratio = ratio
        self.transformations = transformations or ['random_noise', 'row_shuffle']

    def augment_csv(self, input_path: str, output_dir: str, target_column: str = None) -> Dict[str, Any]:
        """
        Augment CSV tabular data.
        
        Args:
            input_path: Path to input CSV file
            output_dir: Directory to save augmented data
            target_column: Optional target column for SMOTE
            
        Returns:
            Statistics about the augmentation
        """
        import pandas as pd

        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        df = pd.read_csv(input_path)
        total_original = len(df)

        augmented_rows = []

        if target_column and target_column in df.columns:
            smote_available = self._try_smote_augmentation(df, target_column)
            if smote_available:
                augmented_rows.extend(smote_available)

        num_to_generate = int((self.ratio - 1) * total_original)
        
        for _ in range(num_to_generate):
            aug_row = self._augment_row_with_noise(df.sample(1).iloc[0])
            augmented_rows.append(aug_row)

        if not augmented_rows:
            for _ in range(int((self.ratio - 1) * total_original)):
                aug_row = self._augment_row_with_noise(df.sample(1).iloc[0])
                augmented_rows.append(aug_row)

        result_df = pd.concat([df, pd.DataFrame(augmented_rows)], ignore_index=True)

        output_file = output_dir / f"augmented_{input_path.name}"
        result_df.to_csv(output_file, index=False)

        return {
            'original_count': total_original,
            'augmented_count': len(augmented_rows),
            'total_count': len(result_df),
            'output_file': str(output_file),
            'columns': list(df.columns),
            'strategy': self.strategy,
            'ratio': self.ratio,
        }

    def _try_smote_augmentation(self, df: pd.DataFrame, target_column: str) -> List[Dict]:
        """Try SMOTE augmentation if available."""
        try:
            from imblearn.over_sampling import SMOTE
            from sklearn.preprocessing import LabelEncoder

            X = df.drop(columns=[target_column])
            y = df[target_column]

            numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) < 2:
                return []

            X_numeric = X[numeric_cols].fillna(0)

            if y.dtype == 'object':
                le = LabelEncoder()
                y_encoded = le.fit_transform(y)
            else:
                y_encoded = y

            smote = SMOTE(random_state=42)
            X_resampled, y_resampled = smote.fit_resample(X_numeric, y_encoded)

            augmented_rows = []
            original_cols = df.columns.tolist()

            for i in range(len(X_resampled) - len(df)):
                new_row = {}
                for col in numeric_cols:
                    new_row[col] = X_resampled.iloc[len(df) + i][col]
                for col in df.columns:
                    if col not in numeric_cols:
                        new_row[col] = df[col].iloc[i % len(df)]
                new_row[target_column] = y_resampled[len(df) + i] if y.dtype == 'object' else y.iloc[i % len(df)]
                augmented_rows.append(new_row)

            return augmented_rows

        except ImportError:
            logger.warning("imblearn not available for SMOTE")
            return []
        except Exception as e:
            logger.warning(f"SMOTE augmentation failed: {e}")
            return []

    def _augment_row_with_noise(self, row: pd.Series) -> pd.Series:
        """Add Gaussian noise to numeric columns of a row."""
        aug_row = row.copy()

        numeric_cols = row.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if pd.notna(aug_row[col]):
                std = max(abs(aug_row[col]) * 0.1, 0.1)
                noise = np.random.normal(0, std)
                aug_row[col] = aug_row[col] + noise

        return aug_row

    def augment_dataset(self, input_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Augment tabular dataset (entry point).
        
        Args:
            input_path: Path to input CSV file
            output_dir: Directory to save augmented data
            
        Returns:
            Statistics about the augmentation
        """
        return self.augment_csv(input_path, output_dir)


# =============================================================================
# Factory function
# =============================================================================

def get_augmentor(data_type: str, strategy: str = 'all', ratio: float = 2.0, 
                  transformations: List[str] = None):
    """
    Factory function to get the appropriate augmentor.
    
    Args:
        data_type: Type of data ('image', 'text', 'tabular')
        strategy: Augmentation strategy
        ratio: Augmentation ratio
        transformations: List of specific transformations
        
    Returns:
        Appropriate augmentor instance
    """
    if data_type == 'image':
        return ImageAugmentor(strategy=strategy, ratio=ratio, transformations=transformations)
    elif data_type == 'text':
        return TextAugmentor(strategy=strategy, ratio=ratio, transformations=transformations)
    elif data_type == 'tabular':
        return TabularAugmentor(strategy=strategy, ratio=ratio, transformations=transformations)
    else:
        raise ValueError(f"Unknown data type: {data_type}")


def detect_data_type(dataset) -> str:
    """
    Detect data type from dataset.
    
    Args:
        dataset: Dataset model instance
        
    Returns:
        Data type string ('image', 'text', 'tabular')
    """
    format_type = getattr(dataset, 'format', 'csv')
    file_path = getattr(dataset, 'file_path', '')
    columns = getattr(dataset, 'columns', [])
    metadata = getattr(dataset, 'metadata', {})

    if format_type in ['image', 'png', 'jpg', 'jpeg']:
        return 'image'
    
    detected_type = metadata.get('data_type', '')
    if detected_type in ['image', 'text', 'tabular']:
        return detected_type

    if format_type in ['text', 'txt']:
        return 'text'
    
    if format_type in ['csv', 'parquet']:
        if columns and len(columns) > 1:
            return 'tabular'
        return 'text'
    
    if format_type in ['json']:
        return 'text'

    if columns and len(columns) > 5:
        return 'tabular'

    return 'text'
