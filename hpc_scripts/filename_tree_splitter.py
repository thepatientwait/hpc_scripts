class FilenameTreeSplitter:
    def chunks(self, split_lengths, input_filename):
        chunks = []
        index = 0
        for length in split_lengths:
            if index + length > len(input_filename):
                break
            chunks.append(input_filename[index:(index+length)])
            index = index + length
        # if index < len(input_filename):
        #     chunks.append(input_filename[index:])
        return chunks