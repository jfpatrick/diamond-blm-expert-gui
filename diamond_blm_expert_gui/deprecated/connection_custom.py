"""Implementation of the signal-based updates to the graph."""

import warnings
import collections
import numpy as np
from typing import Optional, Callable, cast, Type, Sequence, Union, Any, Tuple, List, Dict
from datetime import datetime
from qtpy.QtCore import QObject, Signal, Slot
from accwidgets.graph import (DEFAULT_COLOR, BarCollectionData, BarData, CurveData, TimestampMarkerCollectionData,
                              TimestampMarkerData, InjectionBarCollectionData, InjectionBarData, PointData,
                              PlottingItemData)


class UpdateSource(QObject):
    """
    This class is a proxy of the actual source of data. It declares signals
    that can be used to publish any changes related to the displayed data.
    Convenience functions, such as
    :meth:`.ExPlotWidget.addCurve` of
    :class:`.ExPlotWidget`,
    setup these connections automatically to receive the data from the UpdateSource.

    Additionally, UpdateSource can be used to publish supplemental information to the
    plot, e.g. timestamps that are used by the plot as the current time.

    Finally, UpdateSource can be utilized in editable charts to propagate user changes
    to the control system. This requires re-implementing :meth:`handle_data_model_edit`
    slot.
    """

    # TODO: Range Change Signal not used yet.
    #       Change dict to fitting type when integrated.
    # sig_new_time_span = Signal(dict)
    sig_new_timestamp = Signal(float)
    """Publishes new actual time to the receiver."""

    sig_new_data = Signal("PyQt_PyObject")
    """Publishes a new data sample wrapped in an appropriate data structure."""

    @Slot(CurveData)
    def handle_data_model_edit(data: CurveData):
        """
        Handler for changes made to the data model from the view. It is meant
        to propagate data edited by user to the source, where the data originally came from.

        Args:
            data: Complete data set containing user changes.
        """
        pass

    def new_data(self, data: PlottingItemData):
        """Deprecated, use :meth:`send_data` instead."""
        warnings.warn("UpdateSource.new_data is deprecated. "
                      "Use UpdateSource.send_data instead.",
                      DeprecationWarning)
        self.send_data(data)

    def send_data(self, data: PlottingItemData):
        """Convenience function for sending data through :attr:`sig_new_data`

        Args:
            data: Data which should be sent through the signal.
        """
        self.sig_new_data.emit(data)


class SignalBoundDataSource(UpdateSource):

    def __init__(
            self,
            sig: Signal,
            data_type: Optional[Type[PlottingItemData]] = None,
            transformation: Optional[
                Callable[[Sequence[Union[float, str]]], PlottingItemData]
            ] = None,
    ):
        """
        Convenience subclass of :class:`UpdateSource` for a signal
        with a specific data-type. Instances of this source
        will listen to the provided signal, and package the data to be sent further
        through either the default transformation function, or a user-defined one, if given.

        Details about default transformations can be found in :meth:`PlottingItemDataFactory.get_transformation`.

        Args:
            sig: Signal where the new values are coming from.
            data_type: Output type, which also influences the default transformation to be applied to
                       incoming data, when no ``transformation`` is given. It can be omitted, when
                       ``transformation`` is provided.
            transformation: Optional transformation function to be applied to the incoming data.
        """
        super().__init__(parent=None)
        data_type_specified = data_type is not None
        transform_specified = transformation is not None

        if data_type_specified == transform_specified:
            raise ValueError("You must specify either data_type or transformation")
        self._data_type = data_type
        self.transform: Callable = (transformation
                                    or PlottingItemDataFactory.get_transformation(data_type))
        sig.connect(self._emit_point)

    def _emit_point(self,
                    *args: Union[float, str, Sequence[float], Sequence[str]]):
        if (
            self._data_type is not None
            and len(args) == 1
            and PlottingItemDataFactory.should_unwrap(args[0], self._data_type)
        ):
            transformed_data = self.transform(*args[0])  # type: ignore
        else:
            transformed_data = self.transform(*args)
        self.send_data(transformed_data)


class PlottingItemDataFactory:
    """
    Collection of factory methods for transforming data inside :class:`.UpdateSource`
    instances. E.g. it can repackage :obj:`float` values into
    :class:`.PlottingItemData` objects.
    """

    TIMESTAMP_HEADER_FIELD = "acqStamp"
    """Name of the timestamp meta-field inside JAPC/RDA packets."""

    @staticmethod
    def transform(
        dtype: Type[PlottingItemData],
        *values: Union[float, str, Sequence[float], Sequence[str]],
    ) -> PlottingItemData:
        """
        Transform the values into the given type.

        Args:
            dtype: Desired output type.
            *values: Variable amount of incoming values.

        Returns:
             Packaged data structure.
        """
        transform_func = PlottingItemDataFactory.get_transformation(dtype)
        if (
            PlottingItemDataFactory.should_unwrap(values[0], dtype)
            and len(values) == 1
        ):
            return transform_func(*values[0])
        else:
            return transform_func(*values)

    @staticmethod
    def should_unwrap(value: Any, dtype: Type[PlottingItemData]) -> bool:
        """
        Check if the value should be unwrapped before handed over to the transformation function.
        Incoming argument lists maybe either timestamp-value pairs or simply value as a collection
        of primitives.

        Args:
            value: Value that will be passed to the transformation function.
            dtype: Data type into which the value should be transformed.

        Returns:
            Whether the values should be unwrapped.
        """
        seqs = (collections.Sequence, np.ndarray)
        if isinstance(value, seqs) and not isinstance(value, str):
            if dtype.is_collection:
                return isinstance(value[0], seqs) and not isinstance(value, str)
            return True
        return False

    @staticmethod
    def get_transformation(data_type: Optional[Type[PlottingItemData]]) -> Callable[[], PlottingItemData]:
        """
        Selects the best fitting transformation function fo the given data type.

        Args:
            data_type: Desired target data type.

        Returns:
            Function pointer of the transformation function.

        Raises:
            TypeError: Unsupported data type.
        """
        if data_type is not None:
            if issubclass(data_type, PointData):
                return PlottingItemDataFactory._to_point
            if issubclass(data_type, BarData):
                return PlottingItemDataFactory._to_bar
            if issubclass(data_type, InjectionBarData):
                return PlottingItemDataFactory._to_injection_bar
            if issubclass(data_type, TimestampMarkerData):
                return PlottingItemDataFactory._to_ts_marker
            if issubclass(data_type, CurveData):
                return PlottingItemDataFactory._to_curve
            if issubclass(data_type, BarCollectionData):
                return PlottingItemDataFactory._to_bar_collection
            if issubclass(data_type, InjectionBarCollectionData):
                return PlottingItemDataFactory._to_injection_bar_collection
            if issubclass(data_type, TimestampMarkerCollectionData):
                return PlottingItemDataFactory._to_ts_marker_collection
        raise TypeError("No default transformation function could be found"
                        f"for data type '{data_type}'")

    @staticmethod
    def _to_point(*args: float) -> PointData:  # last argument can be header dict
        arguments, timestamp = PlottingItemDataFactory._separate(*args)
        return PointData(
            x=PlottingItemDataFactory._or_now(index=1,
                                              args=arguments,
                                              acq_timestamp=timestamp),
            y=arguments[0],  # mandatory
        )

    @staticmethod
    def _to_bar(*args: float) -> BarData:  # last argument can be header dict
        arguments, timestamp = PlottingItemDataFactory._separate(*args)
        return BarData(
            x=PlottingItemDataFactory._or_now(index=2,
                                              args=arguments,
                                              acq_timestamp=timestamp),
            y=PlottingItemDataFactory._or(index=1,
                                          args=arguments,
                                          default=0),
            height=arguments[0],  # mandatory
        )

    @staticmethod
    def _to_injection_bar(
            *args: Union[float, str],
    ) -> InjectionBarData:  # last argument can be header dict
        """
        **Attention**: String parameters will automatically set as label,
        no matter where they are positioned.
        """
        arguments, timestamp = PlottingItemDataFactory._separate(*args)
        label = ""
        str_param = [i for i in arguments if isinstance(i, str)]
        if str_param:
            label = str_param[0]
            arguments.remove(label)
        return InjectionBarData(
            x=PlottingItemDataFactory._or_now(index=3,
                                              args=arguments,
                                              acq_timestamp=timestamp),
            y=PlottingItemDataFactory._or(index=1,
                                          args=arguments,
                                          default=np.nan),
            width=PlottingItemDataFactory._or(index=2,
                                              args=arguments,
                                              default=np.nan),
            height=arguments[0],  # mandatory
            label=label,
        )

    @staticmethod
    def _to_ts_marker(
            *args: Union[float, str],
    ) -> TimestampMarkerData:  # last argument can be header dict
        arguments, timestamp = PlottingItemDataFactory._separate(*args)
        return TimestampMarkerData(
            x=PlottingItemDataFactory._or_now(index=0,
                                              args=arguments,
                                              acq_timestamp=timestamp),
            color=PlottingItemDataFactory._or(index=2,
                                              args=arguments,
                                              default=DEFAULT_COLOR),
            label=PlottingItemDataFactory._or(index=1,
                                              args=arguments,
                                              default=""),
        )

    @staticmethod
    def _to_curve(
        *args: Sequence[float],
    ) -> CurveData:  # last argument can be header dict
        arguments, _ = PlottingItemDataFactory._extract_header(list(args))
        return CurveData(
            x=PlottingItemDataFactory._or_num_range(index=1,
                                                    args=arguments),
            y=arguments[0],
        )

    @staticmethod
    def _to_bar_collection(
        *args: Sequence[float],
    ) -> BarCollectionData:  # last argument can be header dict
        arguments, _ = PlottingItemDataFactory._extract_header(list(args))
        return BarCollectionData(
            x=PlottingItemDataFactory._or_num_range(index=2,
                                                    args=arguments),
            y=PlottingItemDataFactory._or_array(index=1,
                                                args=arguments,
                                                default=0),
            heights=arguments[0],
        )

    @staticmethod
    def _to_injection_bar_collection(
            *args: Sequence[Union[float, str]],
    ) -> InjectionBarCollectionData:  # last argument can be header dict
        arguments, _ = PlottingItemDataFactory._extract_header(list(args))
        label = np.zeros(len(arguments[0]), str)
        string_params = [i for i in arguments
                         if not any((not isinstance(j, str) for j in i))]
        if string_params:
            label = string_params[0]
            arguments.remove(label)
        return InjectionBarCollectionData(
            x=PlottingItemDataFactory._or_num_range(index=3,
                                                    args=arguments),
            y=PlottingItemDataFactory._or_array(index=1,
                                                args=arguments,
                                                default=np.nan),
            heights=arguments[0],  # mandatory
            widths=PlottingItemDataFactory._or_array(index=2,
                                                     args=arguments,
                                                     default=np.nan),
            labels=label,
        )

    @staticmethod
    def _to_ts_marker_collection(
            *args: Sequence[Union[float, str]],
    ) -> TimestampMarkerCollectionData:  # last argument can be header dict
        arguments, _ = PlottingItemDataFactory._extract_header(list(args))
        arguments[0] = list(map(float, arguments[0]))
        return TimestampMarkerCollectionData(
            x=cast(Sequence[float], arguments[0]),  # mandatory
            colors=PlottingItemDataFactory._or_array(index=2,
                                                     args=arguments,
                                                     default=DEFAULT_COLOR),
            labels=PlottingItemDataFactory._or_array(index=1,
                                                     args=arguments,
                                                     default=""),
        )

    # Index or Default Argument Functions

    @staticmethod
    def _or_now(index: int,
                args: List[Union[str, float]],
                acq_timestamp: Union[None, float]) -> float:
        """Either the value at the given index, the acquisition timestamp from
        the header or the current time's time stamp locally calculated.
        """
        default = acq_timestamp if acq_timestamp is not None else datetime.now().timestamp()
        return PlottingItemDataFactory._or(index, args, default)

    @staticmethod
    def _or_num_range(index: int,
                      args: List[Sequence[float]]) -> Sequence[float]:
        """Either the value at the given index or a range from 0 to the length
        as one of the entries in args."""
        return PlottingItemDataFactory._or(index,
                                           args,
                                           np.arange(0, len(args[0])))

    @staticmethod
    def _or_array(index: int, args: List[Any], default: Any) -> Any:
        """Return either the value in args at the given index or and array made
        from the passed default value (same length as other args entries)."""
        try:
            return args[index]
        except IndexError:
            return np.array([default for _ in range(len(args[0]))])

    @staticmethod
    def _or(index: int, args: List[Any], default: Any) -> Any:
        """Return either the value in args at the given index or the passed
        default value."""
        try:
            return args[index]
        except IndexError:
            return default

    @staticmethod
    def _separate(*args) -> Tuple[List[Union[float, str]], Optional[float]]:
        """Separate the header's timestamp from the arguments."""
        ts = None
        arguments, header = PlottingItemDataFactory._extract_header(
            list(args))
        if header:
            ts = PlottingItemDataFactory._extract_ts(header)
        return arguments, ts

    @staticmethod
    def _extract_header(args: List) -> Tuple[List, Optional[Dict]]:
        """Remove headers from the last position of the arguments if
        they are there."""
        header: Optional[Dict] = None
        if args and isinstance(args[-1], dict):
            header = args.pop(-1)
        return args, header

    @staticmethod
    def _extract_ts(header: Dict[str, Union[datetime, float]]) -> Optional[float]:
        """
        Extract the timestamp field from the header.
        """
        ts: Union[datetime, float, None] = None
        ts = header.get(PlottingItemDataFactory.TIMESTAMP_HEADER_FIELD)  # type: ignore
        try:
            ts = ts.timestamp()  # type: ignore
        except AttributeError:
            pass  # 'header' == None or 'ts' is float
        return cast(Optional[float], ts)
