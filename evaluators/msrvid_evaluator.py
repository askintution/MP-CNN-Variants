from scipy.stats import pearsonr
import torch
import torch.nn.functional as F

from evaluators.evaluator import Evaluator


class MSRVIDEvaluator(Evaluator):

    def get_scores(self):
        self.model.eval()
        num_classes = self.dataset_cls.NUM_CLASSES
        test_kl_div_loss = 0
        predictions = []
        true_labels = []

        for batch in self.data_loader:
            # Select embedding
            sent1, sent2, sent1_nonstatic, sent2_nonstatic = self.get_sentence_embeddings(batch)

            output = self.model(sent1, sent2, batch.ext_feats, sent1_nonstatic=sent1_nonstatic, sent2_nonstatic=sent2_nonstatic)
            test_kl_div_loss += F.kl_div(output, batch.label, reduction='sum').item()

            predict_classes = torch.arange(0, num_classes, device=batch.label.device).expand(self.batch_size, num_classes)
            # handle last batch which might have smaller size
            if len(predict_classes) != len(batch.sentence_1):
                predict_classes = torch.arange(0, num_classes, device=batch.label.device).expand(len(batch.sentence_1), num_classes)

            true_labels.append((predict_classes * batch.label.detach()).sum(dim=1))
            predictions.append((predict_classes * output.detach().exp()).sum(dim=1))

            del output

        predictions = torch.cat(predictions).cpu().numpy()
        true_labels = torch.cat(true_labels).cpu().numpy()
        test_kl_div_loss /= len(batch.dataset.examples)
        pearson_r = pearsonr(predictions, true_labels)[0]

        return [pearson_r, test_kl_div_loss], ['pearson_r', 'KL-divergence loss']

    def get_final_prediction_and_label(self, batch_predictions, batch_labels):
        num_classes = self.dataset_cls.NUM_CLASSES
        predict_classes = torch.arange(0, num_classes, device=batch_labels.device).expand(batch_predictions.size(0), num_classes)

        predictions = (predict_classes * batch_predictions.exp()).sum(dim=1)
        true_labels = (predict_classes * batch_labels).sum(dim=1)

        return predictions, true_labels
