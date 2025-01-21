import streamlit as st
import itertools
import pandas as pd
import plotly.express as px
import logging

logging.basicConfig(level=logging.DEBUG)


class Cursor:
    def __init__(self, cursor_id, df, data_cols_sel, color_pallet=px.colors.qualitative.Plotly):
        self.id = cursor_id
        self.fig = None
        self.enabled = False
        self.df = None
        self.df_agg = None
        self.col_iter = itertools.cycle(color_pallet)
        # init st elements
        self.enabled = st.checkbox(label=f"Enable Cursor {self.id}", key=f'cursor_{self.id}_enable_cb')
        # copy dataframe
        self.df = df.copy()
        # make cursor slider
        self.min, self.max = st.select_slider(
            label="Cursor 1",
            options=self.df.index,
            value=(self.df.index[0], self.df.index[-1]),
            disabled=(not self.enabled),
            key=f'cursor_{self.id}_slider',
        )
        # slice dataframe and calculate statistics
        if self.enabled:
            try:
                self.df = self.df[data_cols_sel]
                self.df = self.df[self.min:self.max]
                self.df_agg = self.df.agg(['mean', 'std', 'min', 'max'])
                st.dataframe(self.df_agg.transpose())
            except TypeError:
                st.write('Error: selected only numeric waveforms')
            except ValueError:
                st.write('Error: select a waveform')

    def plot(self, fig, fillcolor='lightgrey'):
        if self.enabled:
            # add region to fig
            fig.add_vrect(
                x0=self.min, x1=self.max,
                fillcolor=fillcolor,
                opacity=0.5, line_width=0
            )
            # add lines
            if self.df_agg is not None:
                for col_name, col in self.df_agg.items():
                    fig.add_shape(
                        type="line",
                        x0=self.min, x1=self.max,
                        y0=col['mean'], y1=col['mean'],
                        line_color=next(self.col_iter),
                    )

class DataVisualizer:
    def __init__(self):
        st.set_page_config(page_title='Data Visualizer', layout='wide', initial_sidebar_state='auto')
        self.cursors = []
        self.file_type = None

    def run(self):
        # streamlit title
        st.title("Data Visualizer")

        with st.sidebar:
            st.subheader("Select Data")

            # load data
            data_file = st.file_uploader(
                label="Upload data here",
                key="_data_file",
                type=["csv"]
            )
            if data_file is not None:
                if data_file.type == 'text/csv':
                    logging.debug(f"File uploaded (CSV): {data_file.name} ({data_file.size} bytes)")
                    self.file_type = 'csv'
                elif data_file.type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                    logging.debug(f"File uploaded (Excel): {data_file.name} ({data_file.size} bytes)")
                    self.file_type = 'xls'
                else:
                    logging.error(f"Unknown file type: {data_file.name} ({data_file.size})")
                    return

            # file configurations
            with st.expander("Advanced data configuration", expanded=True):
                # input: skip extra rows when loading df
                skip_rows = st.number_input(
                    label="Number of rows to skip",
                    key="_skip_rows",
                    min_value=0,
                    disabled=(data_file is None)
                )

                # load data file
                if data_file is not None:
                    df = pd.read_csv(data_file, skiprows=skip_rows)
                    df.dropna(axis='columns', inplace=True)

                # input: select index column
                index_opt = []
                data_opt = []
                if 'df' in locals():
                    index_opt = df.columns
                    data_opt = df.select_dtypes(include='number').columns
                # input selection box
                index = st.selectbox(
                    label="Select an index",
                    key="_index",
                    options=[None, *index_opt],
                    disabled=(data_file is None)
                )

                # remove index from data stream options
                if index:
                    if index in data_opt:
                        data_opt=data_opt.drop(index)

                # input: select data columns
                data_cols_sel = st.multiselect(
                    label="Select waveforms",
                    options=data_opt,
                    key="_data_cols_sel",
                    default=data_opt,
                    label_visibility="visible"
                )

            # data cursors
            num_cursors = 3
            cursor_fillcolors = px.colors.qualitative.Pastel1
            if 'df' in locals():
                # define colour palate for graph
                col_pal = px.colors.qualitative.Plotly
                if index:
                    df_temp=df.set_index(index)
                else:
                    df_temp=df
                with st.expander("Cursors", expanded=True):
                    for idx in range(1, num_cursors+1):
                        self.cursors.append(Cursor(idx, df_temp, data_cols_sel))
        ### END SIDEBAR

        if 'df' in locals():
            # create fig for waveforms
            st.write("### Graph")
            try:
                fig = px.line(df, x=index, y=data_cols_sel, color_discrete_sequence=col_pal)
                # plot cursors on fig
                for idx, cursor in enumerate(self.cursors):
                    cursor.plot(fig, fillcolor=cursor_fillcolors[idx])
                # draw chart
                st.plotly_chart(fig)
            except ValueError as e:
                st.write('Error: cannot draw current waveforms')
                print(e)

            # draw table
            st.write("### Raw Data Table")
            st.dataframe(df)

if __name__ == "__main__":
    app = DataVisualizer()
    app.run()
