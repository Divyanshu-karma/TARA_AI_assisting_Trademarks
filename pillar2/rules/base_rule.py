# # pillar2/rules/base_rule.py

# from abc import ABC, abstractmethod
# from pillar2.models import SubsectionFinding


# class IdentificationRule(ABC):

#     tmep_section: str

#     @abstractmethod
#     def evaluate(self, text: str, context=None) -> SubsectionFinding:
#         pass

# pillar2/rules/base_rule.py

from abc import ABC, abstractmethod
from pillar2.models import SubsectionFinding


class IdentificationRule(ABC):

    tmep_section: str

    @abstractmethod
    def evaluate(self, text: str, context=None) -> SubsectionFinding:
        pass